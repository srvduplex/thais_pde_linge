"""Verification nocturne (22h, fermeture des checkin) : compare le besoin en
linge recalcule avec les reservations a jour contre la commande Elis du lundi
(snapshot), pour detecter si des chambres ajoutees depuis la commande entament
le stock de securite avant la prochaine livraison du vendredi.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os

from linge_commande import (
    compute_needs_from_bookings,
    fetch_bookings,
    thais_login,
)


def active_friday(today: datetime.date) -> datetime.date:
    """Vendredi de debut de la fenetre de stock en cours (celle couverte par la
    derniere commande du lundi)."""

    days_since_friday = (today.weekday() - 4) % 7
    return today - datetime.timedelta(days=days_since_friday)


def compute_delta_report(
    snapshot_quantities: dict,
    current_quantities: dict,
    *,
    safety_stock_pct: float,
) -> dict:
    report = {}
    for code in snapshot_quantities:
        ordered = snapshot_quantities.get(code, 0)
        current = current_quantities.get(code, 0)
        delta = current - ordered
        safety_stock = int(safety_stock_pct * ordered)
        at_risk = delta > safety_stock
        report[code] = {
            "ordered": ordered,
            "current": current,
            "delta": delta,
            "safety_stock": safety_stock,
            "at_risk": at_risk,
            "suggested_topup": (delta - safety_stock) if at_risk else 0,
        }
    return report


def any_at_risk(report: dict) -> bool:
    return any(entry["at_risk"] for entry in report.values())


def build_status_email_html(report: dict, config, *, window_from: str, window_to: str) -> str:
    at_risk_codes = [code for code, entry in report.items() if entry["at_risk"]]

    html = [f"<div><p>Fenetre de stock en cours : {window_from} au {window_to}.</p>"]

    if not at_risk_codes:
        html.append("<p><strong>RAS</strong> — les chambres ajoutees depuis la commande du lundi restent dans le stock de securite pour toutes les references.</p>")
        html.append("</div>")
        return "\n".join(html)

    html.append(
        "<p><strong>Attention</strong> — des chambres ont ete ajoutees depuis la commande du lundi au point "
        "d'entamer le stock de securite sur les references suivantes :</p>"
    )
    html.append('<table border="1" cellspacing="0" cellpadding="4">')
    html.append("<tr><th>Code</th><th>Désignation</th><th>Commandé</th><th>Besoin actuel</th><th>Delta</th><th>Stock sécurité</th><th>Complément suggéré</th></tr>")
    for code in at_risk_codes:
        entry = report[code]
        designation = config.referentiel.get(code, {}).get("designation", code)
        html.append(
            f"<tr><td>{code}</td><td>{designation}</td><td>{entry['ordered']}</td>"
            f"<td>{entry['current']}</td><td>+{entry['delta']}</td><td>{entry['safety_stock']}</td>"
            f"<td>{entry['suggested_topup']}</td></tr>"
        )
    html.append("</table>")
    html.append("</div>")
    return "\n".join(html)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verification nocturne du stock de linge")
    parser.add_argument("--config", required=True, metavar="FICHIER", help="Config hotel/fournisseur (configs/*.json)")
    parser.add_argument("--snapshot-json", required=True, metavar="FICHIER", help="Snapshot de la commande du lundi (--snapshot-json de linge_commande.py)")
    parser.add_argument("--bookings-json", metavar="FICHIER", help="Reservations Thais deja telechargees (mode hors-ligne / test)")
    parser.add_argument("--base-url", help="Sinon utilise base_url de la config")
    parser.add_argument("--username", help="Identifiant API Thais (sinon variable THAIS_USERNAME)")
    parser.add_argument("--password", help="Mot de passe API Thais (sinon variable THAIS_PASSWORD)")
    parser.add_argument("--safety-stock-pct", type=float, default=0.20)
    parser.add_argument("--notify-smtp", action="store_true")
    args = parser.parse_args(argv)

    import config as cfg

    hotel_config = cfg.load_config(args.config)
    base_url = args.base_url or hotel_config.base_url

    with open(args.snapshot_json, encoding="utf-8") as f:
        snapshot = json.load(f)

    date_from = datetime.date.fromisoformat(snapshot["from_date"])
    date_to = datetime.date.fromisoformat(snapshot["to_date"])

    if args.bookings_json:
        with open(args.bookings_json, encoding="utf-8") as f:
            bookings = json.load(f)
    else:
        username = args.username or os.environ.get("THAIS_USERNAME")
        password = args.password or os.environ.get("THAIS_PASSWORD")
        if not username or not password:
            parser.error("--username/--password (ou THAIS_USERNAME/THAIS_PASSWORD) requis sans --bookings-json")
        token = thais_login(base_url, username, password)
        bookings = fetch_bookings(base_url, token, snapshot["from_date"], snapshot["to_date"])

    current_quantities = compute_needs_from_bookings(bookings, date_from, date_to, hotel_config)
    report = compute_delta_report(snapshot["quantities"], current_quantities, safety_stock_pct=args.safety_stock_pct)

    for code, entry in report.items():
        flag = " /!\\ A RISQUE" if entry["at_risk"] else ""
        print(f"{code}: commande={entry['ordered']} actuel={entry['current']} delta=+{entry['delta']} stock_secu={entry['safety_stock']}{flag}")

    html = build_status_email_html(report, hotel_config, window_from=snapshot["from_date"], window_to=snapshot["to_date"])
    print()
    print(html)

    if args.notify_smtp:
        from linge_commande import send_notification_email

        smtp_username = os.environ.get("SMTP_USERNAME")
        smtp_app_password = os.environ.get("SMTP_APP_PASSWORD")
        smtp_from = os.environ.get("SMTP_FROM", smtp_username)
        # Alerte interne (stock a risque) : distinct de SMTP_TO qui, depuis le
        # passage a l'envoi direct fournisseur, sert a la commande hebdomadaire.
        smtp_to = os.environ.get("ALERT_SMTP_TO", smtp_username)
        if not smtp_username or not smtp_app_password:
            parser.error("--notify-smtp requiert SMTP_USERNAME et SMTP_APP_PASSWORD dans l'environnement")

        status = "ALERTE stock" if any_at_risk(report) else "RAS"
        subject = f"[{status}] Verif stock linge 22h {hotel_config.hotel_name} — semaine du {snapshot['from_date']} au {snapshot['to_date']}"
        send_notification_email(
            html,
            smtp_username=smtp_username,
            smtp_app_password=smtp_app_password,
            from_addr=smtp_from,
            to_addr=smtp_to,
            subject=subject,
        )
        print(f"\nEmail de statut envoye a {smtp_to}")


if __name__ == "__main__":
    main()
