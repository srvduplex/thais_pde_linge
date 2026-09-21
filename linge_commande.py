"""Calcul du besoin en linge a partir des reservations Thais et generation du
mail de commande pour un hotel donne. Le moteur est partage entre tous les
hotels/fournisseurs ; ce qui differe (referentiel d'articles, dotation par
categorie de chambre, coordonnees) vient d'un fichier de config.HotelConfig
(voir config.py et configs/*.json).

Regle de rotation (cf. echanges avec l'exploitant du Plat d'Etain — a
confirmer/adapter pour tout autre hotel) :
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
    config,
    *,
    sans_bain: bool = False,
    sans_tapis: bool = False,
    triple_sans_90: bool = False,
) -> dict:
    """Calcule le besoin en linge pour les nuits [date_from, date_to] (incluses),
    en tenant compte du jour de sejour reel de chaque reservation (meme si le
    sejour a demarre avant date_from). `config` est un config.HotelConfig
    (referentiel d'articles et dotation propres a l'hotel/fournisseur)."""

    qty = {code: 0 for code in config.referentiel if config.referentiel[code]["section"] != "restaurant"}
    window_end_exclusive = date_to + datetime.timedelta(days=1)

    for booking in bookings:
        if booking.get("canceled") or booking.get("no_show"):
            continue

        start = datetime.date.fromisoformat(booking["start_at"])
        end = datetime.date.fromisoformat(booking["end_at"])

        for booking_room in booking.get("booking_rooms", []):
            room = booking_room.get("room") or {}
            room_type = room.get("room_type") or {}
            categorie = config.room_label_to_categorie.get(room.get("label"))
            if categorie is None:
                categorie = config.label_to_categorie.get(room_type.get("label"))
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
                    dotation = dict(config.dotation_lit[categorie])
                    if categorie == "triple" and triple_sans_90:
                        for code in config.bed_linen_codes_lit90:
                            dotation.pop(code, None)
                    for code, unite in dotation.items():
                        qty[code] += unite
                    for code, unite in config.taies_fixes.items():
                        qty[code] += unite
                    if config.extra_bed_threshold is not None and occupants > config.extra_bed_threshold:
                        for code, unite in config.extra_bed_dotation.items():
                            qty[code] += unite

                if not sans_bain:
                    # drap de bain = grande serviette : meme cycle 2 jours que
                    # la serviette eponge et le tapis (full + partiel).
                    qty[config.drap_bain_code] += occupants
                    qty[config.serviette_code] += occupants
                    if not sans_tapis:
                        qty[config.tapis_bain_code] += config.tapis_par_categorie[categorie]

    return qty


def compute_category_nights(bookings: list, date_from: datetime.date, date_to: datetime.date, config) -> dict:
    """Nombre de nuitees a changement complet par categorie de literie, pour
    le resume ('Chambres Double : 40 nuits') mis en tete de l'email fournisseur."""

    nights = {}
    window_end_exclusive = date_to + datetime.timedelta(days=1)

    for booking in bookings:
        if booking.get("canceled") or booking.get("no_show"):
            continue

        start = datetime.date.fromisoformat(booking["start_at"])
        end = datetime.date.fromisoformat(booking["end_at"])

        for booking_room in booking.get("booking_rooms", []):
            room = booking_room.get("room") or {}
            room_type = room.get("room_type") or {}
            categorie = config.room_label_to_categorie.get(room.get("label"))
            if categorie is None:
                categorie = config.label_to_categorie.get(room_type.get("label"))
            if categorie is None:
                continue

            for night in _daterange(start, end):
                if night < date_from or night >= window_end_exclusive:
                    continue
                day_of_stay = (night - start).days + 1
                if stay_night_kind(day_of_stay) == "full":
                    nights[categorie] = nights.get(categorie, 0) + 1

    return nights


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


def is_order_empty(quantities: dict) -> bool:
    """True si aucune reference n'a de quantite positive (rien a commander,
    ex. pendant une fermeture saisonniere)."""

    return all(qty <= 0 for qty in quantities.values())


def apply_carryover(quantities: dict, carryover: dict) -> dict:
    """Ajoute l'ecart non couvert de la semaine precedente (positif = manque,
    negatif = surplus) pour que le stock revienne au meme niveau cible
    chaque semaine. Plafonne a 0 (un surplus ne peut pas rendre une
    quantite negative)."""

    result = dict(quantities)
    for code, delta in carryover.items():
        if code in result:
            result[code] = max(0, result[code] + delta)
    return result


def apply_minimum_order(quantities: dict, minimum: int) -> dict:
    """Remonte toute quantite strictement positive au minimum de commande du
    fournisseur ; les references a 0 (aucun besoin) restent a 0."""

    return {code: (max(qty, minimum) if qty > 0 else 0) for code, qty in quantities.items()}


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


def _rows_by_section(quantities: dict, config):
    by_section = {"lit": [], "bain": [], "restaurant": []}
    for code, article in config.referentiel.items():
        qte = quantities.get(code, 0)
        if qte <= 0:
            continue
        by_section[article["section"]].append((code, article, qte))
    return by_section


def build_recap_table(quantities: dict, config) -> str:
    lines = [f"{'Code':<8}{'Designation':<36}{'Liseret/Lit':<18}{'Quantite':>8}"]
    lines.append("-" * 70)
    for section in ("lit", "bain", "restaurant"):
        for code, article, qte in _rows_by_section(quantities, config)[section]:
            detail = article["liseret"] if article["liseret"] != "-" else article["dimension"]
            lines.append(f"{code:<8}{article['designation']:<36}{detail:<18}{qte:>8}")
    return "\n".join(lines)


def build_inventory_request_html(config, *, codes: list = None, signature: str = None) -> str:
    """Corps HTML de la demande d'inventaire (linge de lit + linge de bain,
    hors restaurant qui suit un circuit manuel distinct), a envoyer
    periodiquement pour ajuster la commande via apply_stock. `codes`
    restreint la demande a un sous-ensemble (rotation, cf. inventory_request.py)."""

    signature = signature if signature is not None else config.signature
    html = [
        "<div>",
        "<p>Bonjour,</p>",
        "<p>Pour ajuster la commande de linge de la semaine avant la livraison de vendredi, "
        "merci de compter le stock actuel (linge propre, prêt à l'emploi) pour chacune des "
        "références ci-dessous, et de <strong>répondre à cet email</strong> avec les quantités.</p>",
        '<table border="1" cellspacing="0" cellpadding="6">',
        "<tr><th>Code</th><th>Désignation</th><th>Dimension</th><th>Quantité en stock</th></tr>",
    ]
    for code, article in config.referentiel.items():
        if article["section"] not in ("lit", "bain"):
            continue
        if codes is not None and code not in codes:
            continue
        html.append(f"<tr><td>{code}</td><td>{article['designation']}</td><td>{article['dimension']}</td><td></td></tr>")
    html.append("</table>")
    html.append("<p>Merci d'avance,<br>")
    html.append(f"{signature}</p>")
    html.append("</div>")
    return "\n".join(html)


def build_email_html(
    quantities: dict,
    config,
    *,
    footer_note: str = None,
    signature: str = None,
    intro: str = None,
    category_nights: dict = None,
    category_labels: dict = None,
    closing_note: str = None,
) -> str:
    """Genere le corps HTML de l'email de commande. `category_nights` +
    `category_labels` (optionnels) ajoutent le resume en puces ("Chambres
    Double (lit 140) : 40 nuits") utilise historiquement par Mathieu avant le
    tableau detaille, cf. echanges reels avec Elis."""

    footer_note = footer_note if footer_note is not None else config.footer_note
    signature = signature if signature is not None else config.signature
    sections = _rows_by_section(quantities, config)
    html = ["<div>"]
    if intro:
        html.append(f"<p>{intro}</p>")
    if category_nights and category_labels:
        html.append("<ul>")
        for categorie, label in category_labels.items():
            n = category_nights.get(categorie, 0)
            if n > 0:
                html.append(f"<li>{label} : <strong>{n} nuits</strong></li>")
        html.append("</ul>")
    for section in ("lit", "bain", "restaurant"):
        rows = sections[section]
        if not rows:
            continue
        html.append(f"<h3>{SECTION_TITLES[section]}</h3>")
        html.append('<table border="1" cellspacing="0" cellpadding="4">')
        html.append("<tr><th>Code</th><th>Description</th><th>Dimension</th><th>Quantité</th></tr>")
        for code, article, qte in rows:
            html.append(f"<tr><td>{code}</td><td>{article['designation']}</td><td>{article['dimension']}</td><td>{qte}</td></tr>")
        html.append("</table>")
    html.append(f"<p>{footer_note}</p>")
    if closing_note:
        html.append(f"<p>{closing_note}</p>")
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
    cc_addr: str = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> None:
    """Envoie (immediatement, pas un brouillon) un email par SMTP. to_addr/cc_addr
    acceptent plusieurs adresses separees par des virgules. Authentification SMTP
    avec un mot de passe d'application ; from_addr peut etre un alias "Envoyer en
    tant que" verifie sur le compte smtp_username, Gmail l'honorera alors."""

    import smtplib
    import ssl
    from email.mime.text import MIMEText

    message = MIMEText(html_body, "html")
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    if cc_addr:
        message["Cc"] = cc_addr

    to_list = [addr.strip() for addr in to_addr.split(",") if addr.strip()]
    cc_list = [addr.strip() for addr in cc_addr.split(",") if addr.strip()] if cc_addr else []

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_username, smtp_app_password)
        server.sendmail(from_addr, to_list + cc_list, message.as_string())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Commande linge — genere le besoin pour un hotel donne")
    parser.add_argument("--config", required=True, metavar="FICHIER", help="Config hotel/fournisseur (configs/*.json)")
    parser.add_argument("--from-date", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--bookings-json", metavar="FICHIER", help="Reservations Thais deja telechargees (mode hors-ligne / test)")
    parser.add_argument("--base-url", help="Sinon utilise base_url de la config")
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
    parser.add_argument("--carryover-file", metavar="FICHIER", help="Ajoute l'ecart non couvert de la semaine precedente (calcule par verif_stock.py) et le remet a zero une fois absorbe")
    parser.add_argument("--order-log", metavar="FICHIER", help="Log des commandes envoyees (garde-fou anti-doublon + historique pour controle de facturation)")
    parser.add_argument("--force-resend", action="store_true", help="Ignore le garde-fou anti-doublon et envoie quand meme")
    args = parser.parse_args(argv)

    import config as cfg

    hotel_config = cfg.load_config(args.config)
    base_url = args.base_url or hotel_config.base_url

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
        token = thais_login(base_url, username, password)
        bookings = fetch_bookings(base_url, token, args.from_date, args.to_date)

    quantities = compute_needs_from_bookings(
        bookings,
        date_from,
        date_to,
        hotel_config,
        sans_bain=args.sans_bain,
        sans_tapis=args.sans_tapis,
        triple_sans_90=args.triple_sans_90,
    )
    if args.carryover_file:
        import stock_history as sh

        carryover = sh.load_carryover(args.carryover_file)
        quantities = apply_carryover(quantities, carryover)

    if args.stock:
        quantities = apply_stock(quantities, args.stock)

    if hotel_config.minimum_order_qty:
        quantities = apply_minimum_order(quantities, hotel_config.minimum_order_qty)

    if args.snapshot_json:
        with open(args.snapshot_json, "w", encoding="utf-8") as f:
            json.dump(
                {"from_date": args.from_date, "to_date": args.to_date, "quantities": quantities},
                f,
                indent=2,
                ensure_ascii=False,
            )
        if args.carryover_file:
            import stock_history as sh

            sh.save_carryover(args.carryover_file, {})  # ecart absorbe dans cette commande

    quantities["6735"] = args.nappe_12x12
    quantities["6739"] = args.nappe_15x15
    quantities["6820"] = args.serviette_table

    print(build_recap_table(quantities, hotel_config))
    print()

    category_nights = None
    if hotel_config.category_labels:
        category_nights = compute_category_nights(bookings, date_from, date_to, hotel_config)

    html = build_email_html(
        quantities,
        hotel_config,
        intro=hotel_config.email_intro or None,
        category_nights=category_nights,
        category_labels=hotel_config.category_labels or None,
        closing_note=hotel_config.email_closing or None,
    )
    print(html)

    if args.out_html:
        with open(args.out_html, "w", encoding="utf-8") as f:
            f.write(html)

    if is_order_empty(quantities):
        print("\nCommande entierement vide (0 sur toutes les references) — aucun envoi (--draft/--notify-smtp ignores).")
        return

    if args.draft:
        draft_id = create_gmail_draft(html)
        print(f"\nBrouillon Gmail cree : {draft_id}")

    if args.notify_smtp:
        import os

        import order_log as ol

        if args.order_log and not args.force_resend and ol.has_already_sent(args.order_log, args.from_date, args.to_date):
            print(
                f"\n/!\\ Une commande a deja ete envoyee pour cette fenetre ({args.from_date} -> {args.to_date}) "
                f"— envoi ignore pour eviter un doublon. Utilisez --force-resend pour passer outre."
            )
            return

        smtp_username = os.environ.get("SMTP_USERNAME")
        smtp_app_password = os.environ.get("SMTP_APP_PASSWORD")
        smtp_from = os.environ.get("SMTP_FROM", smtp_username)
        smtp_to = os.environ.get("SMTP_TO", smtp_username)
        smtp_cc = os.environ.get("SMTP_CC")
        if not smtp_username or not smtp_app_password:
            parser.error("--notify-smtp requiert SMTP_USERNAME et SMTP_APP_PASSWORD dans l'environnement")
        subject = f"Commande linge {hotel_config.hotel_name} — semaine du {args.from_date} au {args.to_date}"
        send_notification_email(
            html,
            smtp_username=smtp_username,
            smtp_app_password=smtp_app_password,
            from_addr=smtp_from,
            cc_addr=smtp_cc,
            to_addr=smtp_to,
            subject=subject,
        )
        cc_note = f", cc {smtp_cc}" if smtp_cc else ""
        print(f"\nEmail envoye a {smtp_to}{cc_note} (from {smtp_from})")

        if args.order_log:
            order_number = ol.compute_order_number(date_from, hotel_config.hotel_code)
            ol.record_sent_order(
                args.order_log,
                order_number=order_number,
                date_sent=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                from_date=args.from_date,
                to_date=args.to_date,
                to_email=smtp_to,
                cc_email=smtp_cc,
                quantities=quantities,
            )
            print(f"Commande enregistree dans le log ({args.order_log}) : {order_number}")


if __name__ == "__main__":
    main()
