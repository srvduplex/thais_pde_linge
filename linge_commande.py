"""Calcul du besoin en linge (Elis) a partir des reservations Thais et
generation du mail de commande pour Le Plat d'Etain.

Regle de rotation (cf. echanges avec l'exploitant) :
- Jour 1 du sejour (arrivee) = changement complet (lit + bain).
- Tous les 4 jours ensuite (jour 5, 9, 13...) = nouvelle "mise a blanc"
  complete du LIT (draps/housses/taies), qui s'ajoute au changement de
  linge de bain qui aurait de toute facon lieu ce jour-la.
- Les autres jours impairs (jour 3, 7, 11... hors mise a blanc) = changement
  de linge de BAIN uniquement : drap de bain (= grande serviette), serviette
  eponge, tapis de bain. Le linge de bain suit donc le meme cycle (2 jours)
  quel que soit le jour ; seul le linge de lit attend la mise a blanc (4 jours).
- Les jours pairs : aucun changement (le linge du dernier passage est garde).
- Les oreillers (2 taies carrees + 2 taies rectangulaires) sont poses par
  question d'esthetisme des qu'il y a un changement complet du lit, quelle
  que soit la categorie de chambre ou le nombre d'occupants.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
import urllib.error
import urllib.request


# ---------------------------------------------------------------------------
# Referentiel articles Elis
# ---------------------------------------------------------------------------

REFERENTIEL = {
    # Draps plats
    "1341": {"designation": "Drap Clas blc l.orang 180 NF", "dimension": "180x285", "liseret": "Orange", "section": "lit"},
    "2941": {"designation": "Drap Clas blc l. noir 280 NF", "dimension": "280x285", "liseret": "Noir", "section": "lit"},
    "11143": {"designation": "Drap Clas blc 2l. noir 310 NF", "dimension": "310x305", "liseret": "Double noir", "section": "lit"},
    # Housses de couette
    "41113": {"designation": "Housse Stella S l.anis blc NF", "dimension": "160x260", "liseret": "Anis", "section": "lit"},
    "32830": {"designation": "Housse Stella S l.marron blc NF", "dimension": "230x260", "liseret": "Marron", "section": "lit"},
    "41115": {"designation": "Housse Stella l. bleu marine NF", "dimension": "265x260", "liseret": "Bleu marine", "section": "lit"},
    # Taies (fixes : 2 carrees + 2 rectangulaires par chambre a chaque changement complet)
    "43128": {"designation": "Taie Car Clas l.vert 65x65", "dimension": "65x65", "liseret": "Vert", "section": "lit"},
    "517": {"designation": "Taie Am Clas blc 50x80 NF", "dimension": "50x80", "liseret": "-", "section": "lit"},
    # Linge de bain
    "8786": {"designation": "Drap bain Confort blc", "dimension": "-", "liseret": "-", "section": "bain"},
    "8785": {"designation": "Serv Eponge Confort blc", "dimension": "-", "liseret": "-", "section": "bain"},
    "8787": {"designation": "Tapis bain Confort blc", "dimension": "-", "liseret": "-", "section": "bain"},
    # Restaurant (quantites saisies manuellement)
    "6735": {"designation": "Nappe 12x12", "dimension": "-", "liseret": "-", "section": "restaurant"},
    "6739": {"designation": "Nappe 15x15", "dimension": "-", "liseret": "-", "section": "restaurant"},
    "6820": {"designation": "Serviette de table", "dimension": "-", "liseret": "-", "section": "restaurant"},
}

# Categorie de chambre Thais -> categorie de literie interne.
LABEL_TO_CATEGORIE = {
    "Chambre Double Supérieur": "double",
    "Chambre Double Classique": "double",
    "Chambre Twin Classique": "twin",
    "Chambre Triple": "triple",
}

# Linge de lit pose a chaque changement COMPLET (jour 1, 5, 9...), par categorie.
DOTATION_LIT = {
    "double": {"2941": 1, "32830": 1},
    "twin": {"1341": 2, "41113": 2},
    "triple": {"11143": 1, "1341": 1, "41115": 1, "41113": 1},
}

# Tapis de bain : lie au nombre de lits de la chambre, pose a chaque
# changement (complet OU partiel), pas seulement a la mise a blanc.
TAPIS_PAR_CATEGORIE = {"double": 1, "twin": 2, "triple": 2}

# Oreillers : fixes, independants de la categorie et du nombre d'occupants,
# poses uniquement lors d'un changement complet.
TAIES_FIXES = {"43128": 2, "517": 2}

BED_LINEN_CODES_LIT90 = {"1341", "41113"}  # drap 180 + housse anis : lit 90 des Triple


def stay_night_kind(day_of_stay: int) -> str:
    """Jour 1 = arrivee. Renvoie 'full' (mise a blanc), 'partial' (serviette+tapis)
    ou 'none' selon le cycle 2 jours / 4 jours decrit dans le docstring du module."""

    if day_of_stay % 4 == 1:
        return "full"
    if day_of_stay % 2 == 1:
        return "partial"
    return "none"


def _daterange(start: datetime.date, end: datetime.date):
    current = start
    while current < end:
        yield current
        current += datetime.timedelta(days=1)


def compute_needs_from_bookings(
    bookings: list,
    date_from: datetime.date,
    date_to: datetime.date,
    *,
    sans_bain: bool = False,
    sans_tapis: bool = False,
    triple_sans_90: bool = False,
) -> dict:
    """Calcule le besoin en linge pour les nuits [date_from, date_to] (incluses),
    en tenant compte du jour de sejour reel de chaque reservation (meme si le
    sejour a demarre avant date_from)."""

    qty = {code: 0 for code in REFERENTIEL if REFERENTIEL[code]["section"] != "restaurant"}
    window_end_exclusive = date_to + datetime.timedelta(days=1)

    for booking in bookings:
        if booking.get("canceled") or booking.get("no_show"):
            continue

        start = datetime.date.fromisoformat(booking["start_at"])
        end = datetime.date.fromisoformat(booking["end_at"])

        for booking_room in booking.get("booking_rooms", []):
            room = booking_room.get("room") or {}
            room_type = room.get("room_type") or {}
            categorie = LABEL_TO_CATEGORIE.get(room_type.get("label"))
            if categorie is None:
                continue

            nb_persons = booking_room.get("nb_persons") or {}
            occupants = (nb_persons.get("adults") or 0) + (nb_persons.get("children") or 0)

            for night in _daterange(start, end):
                if night < date_from or night >= window_end_exclusive:
                    continue

                day_of_stay = (night - start).days + 1
                kind = stay_night_kind(day_of_stay)
                if kind == "none":
                    continue

                if kind == "full":
                    dotation = dict(DOTATION_LIT[categorie])
                    if categorie == "triple" and triple_sans_90:
                        for code in BED_LINEN_CODES_LIT90:
                            dotation.pop(code, None)
                    for code, unite in dotation.items():
                        qty[code] += unite
                    for code, unite in TAIES_FIXES.items():
                        qty[code] += unite

                if not sans_bain:
                    # drap de bain = grande serviette : meme cycle 2 jours que
                    # la serviette eponge et le tapis (full + partiel).
                    qty["8786"] += occupants
                    qty["8785"] += occupants
                    if not sans_tapis:
                        qty["8787"] += TAPIS_PAR_CATEGORIE[categorie]

    return qty


def apply_stock(quantities: dict, stock_path: str) -> dict:
    """Soustrait un stock compte par reference (qte finale = max(0, besoin - stock))."""

    stock = {}
    with open(stock_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if not row:
                continue
            code, value = row[0].strip(), row[1].strip()
            if code.lower() == "code":
                continue  # ligne d'en-tete
            stock[code] = int(value)

    result = dict(quantities)
    for code, stock_qty in stock.items():
        if code in result:
            result[code] = max(0, result[code] - stock_qty)
    return result


# ---------------------------------------------------------------------------
# Recuperation des reservations depuis l'API Partner Thais
# ---------------------------------------------------------------------------

def thais_login(base_url: str, username: str, password: str) -> str:
    req = urllib.request.Request(
        f"{base_url}/hub/api/partner/login",
        data=json.dumps({"username": username, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)["token"]
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Authentification Thais echouee ({exc.code}): {exc.read().decode()}") from exc


def fetch_bookings(base_url: str, token: str, date_from: str, date_to: str) -> list:
    url = f"{base_url}/hub/api/partner/hotel/bookings?from={date_from}&to={date_to}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


# ---------------------------------------------------------------------------
# Sorties (console + email)
# ---------------------------------------------------------------------------

SECTION_TITLES = {
    "lit": "Linge de lit",
    "bain": "Linge de bain",
    "restaurant": "Restaurant",
}


def _rows_by_section(quantities: dict):
    by_section = {"lit": [], "bain": [], "restaurant": []}
    for code, article in REFERENTIEL.items():
        qte = quantities.get(code, 0)
        if qte <= 0:
            continue
        by_section[article["section"]].append((code, article, qte))
    return by_section


def build_recap_table(quantities: dict) -> str:
    lines = [f"{'Code':<8}{'Designation':<36}{'Liseret/Lit':<18}{'Quantite':>8}"]
    lines.append("-" * 70)
    for section in ("lit", "bain", "restaurant"):
        for code, article, qte in _rows_by_section(quantities)[section]:
            detail = article["liseret"] if article["liseret"] != "-" else article["dimension"]
            lines.append(f"{code:<8}{article['designation']:<36}{detail:<18}{qte:>8}")
    return "\n".join(lines)


def build_email_html(
    quantities: dict,
    *,
    footer_note: str = "Compte HT2 n° 244968 — tournée 89 — livraison vendredi.",
    signature: str = "Mathieu Tarrade<br>HT2 SARL — Le Plat d'Étain<br>06 02 05 24 99",
) -> str:
    sections = _rows_by_section(quantities)
    html = ["<div>"]
    for section in ("lit", "bain", "restaurant"):
        rows = sections[section]
        if not rows:
            continue
        html.append(f"<h3>{SECTION_TITLES[section]}</h3>")
        html.append('<table border="1" cellspacing="0" cellpadding="4">')
        html.append("<tr><th>Code</th><th>Désignation</th><th>Détail</th><th>Quantité</th></tr>")
        for code, article, qte in rows:
            detail = article["liseret"] if article["liseret"] != "-" else article["dimension"]
            html.append(f"<tr><td>{code}</td><td>{article['designation']}</td><td>{detail}</td><td>{qte}</td></tr>")
        html.append("</table>")
    html.append(f"<p>{footer_note}</p>")
    html.append(f"<p>{signature}</p>")
    html.append("</div>")
    return "\n".join(html)


def create_gmail_draft(html_body: str, to: str = "pauline.padovan@elis.com", subject: str = "Commande linge — Le Plat d'Étain") -> str:
    """Cree un brouillon Gmail via l'API Google (necessite credentials.json / token.json)."""

    try:
        import base64
        from email.mime.text import MIMEText

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Pour utiliser --draft, installez : pip install google-api-python-client "
            "google-auth-httplib2 google-auth-oauthlib"
        ) from exc

    scopes = ["https://www.googleapis.com/auth/gmail.compose"]
    creds = None
    token_path = "token.json"
    try:
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    except FileNotFoundError:
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    message = MIMEText(html_body, "html")
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return draft["id"]


def send_notification_email(
    html_body: str,
    *,
    smtp_username: str,
    smtp_app_password: str,
    from_addr: str,
    to_addr: str,
    subject: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> None:
    """Envoie (immediatement, pas un brouillon) un email recapitulatif a soi-meme,
    pret a copier-coller dans un nouveau message a Elis. Authentification SMTP
    avec un mot de passe d'application ; from_addr peut etre un alias "Envoyer en
    tant que" verifie sur le compte smtp_username, Gmail l'honorera alors."""

    import smtplib
    import ssl
    from email.mime.text import MIMEText

    message = MIMEText(html_body, "html")
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_username, smtp_app_password)
        server.sendmail(from_addr, [to_addr], message.as_string())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Commande linge Elis — Le Plat d'Étain")
    parser.add_argument("--from-date", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--bookings-json", metavar="FICHIER", help="Reservations Thais deja telechargees (mode hors-ligne / test)")
    parser.add_argument("--base-url", default="https://leplatdetain.thais-hotel.com")
    parser.add_argument("--username", help="Identifiant API Thais (sinon variable THAIS_USERNAME)")
    parser.add_argument("--password", help="Mot de passe API Thais (sinon variable THAIS_PASSWORD)")
    parser.add_argument("--sans-bain", action="store_true")
    parser.add_argument("--sans-tapis", action="store_true")
    parser.add_argument("--triple-sans-90", action="store_true")
    parser.add_argument("--stock", metavar="FICHIER")
    parser.add_argument("--nappe-12x12", type=int, default=0)
    parser.add_argument("--nappe-15x15", type=int, default=0)
    parser.add_argument("--serviette-table", type=int, default=0)
    parser.add_argument("--draft", action="store_true", help="Cree directement le brouillon Gmail (necessite credentials.json/token.json)")
    parser.add_argument("--notify-smtp", action="store_true", help="Envoie un email recap a soi-meme par SMTP (SMTP_USERNAME/SMTP_APP_PASSWORD/SMTP_FROM/SMTP_TO)")
    parser.add_argument("--out-html", metavar="FICHIER", help="Sauvegarde le corps HTML dans un fichier")
    parser.add_argument("--snapshot-json", metavar="FICHIER", help="Sauvegarde les quantites commandees (hors restaurant) pour la verification nocturne")
    args = parser.parse_args(argv)

    date_from = datetime.date.fromisoformat(args.from_date)
    date_to = datetime.date.fromisoformat(args.to_date)

    if args.bookings_json:
        with open(args.bookings_json, encoding="utf-8") as f:
            bookings = json.load(f)
    else:
        import os

        username = args.username or os.environ.get("THAIS_USERNAME")
        password = args.password or os.environ.get("THAIS_PASSWORD")
        if not username or not password:
            parser.error("--username/--password (ou THAIS_USERNAME/THAIS_PASSWORD) requis sans --bookings-json")
        token = thais_login(args.base_url, username, password)
        bookings = fetch_bookings(args.base_url, token, args.from_date, args.to_date)

    quantities = compute_needs_from_bookings(
        bookings,
        date_from,
        date_to,
        sans_bain=args.sans_bain,
        sans_tapis=args.sans_tapis,
        triple_sans_90=args.triple_sans_90,
    )
    if args.stock:
        quantities = apply_stock(quantities, args.stock)

    if args.snapshot_json:
        with open(args.snapshot_json, "w", encoding="utf-8") as f:
            json.dump(
                {"from_date": args.from_date, "to_date": args.to_date, "quantities": quantities},
                f,
                indent=2,
                ensure_ascii=False,
            )

    quantities["6735"] = args.nappe_12x12
    quantities["6739"] = args.nappe_15x15
    quantities["6820"] = args.serviette_table

    print(build_recap_table(quantities))
    print()

    html = build_email_html(quantities)
    print(html)

    if args.out_html:
        with open(args.out_html, "w", encoding="utf-8") as f:
            f.write(html)

    if args.draft:
        draft_id = create_gmail_draft(html)
        print(f"\nBrouillon Gmail cree : {draft_id}")

    if args.notify_smtp:
        import os

        smtp_username = os.environ.get("SMTP_USERNAME")
        smtp_app_password = os.environ.get("SMTP_APP_PASSWORD")
        smtp_from = os.environ.get("SMTP_FROM", smtp_username)
        smtp_to = os.environ.get("SMTP_TO", smtp_username)
        if not smtp_username or not smtp_app_password:
            parser.error("--notify-smtp requiert SMTP_USERNAME et SMTP_APP_PASSWORD dans l'environnement")
        subject = f"[A copier vers Elis] Commande linge Elis — semaine du {args.from_date} au {args.to_date}"
        send_notification_email(
            html,
            smtp_username=smtp_username,
            smtp_app_password=smtp_app_password,
            from_addr=smtp_from,
            to_addr=smtp_to,
            subject=subject,
        )
        print(f"\nEmail recap envoye a {smtp_to} (from {smtp_from})")


if __name__ == "__main__":
    main()
