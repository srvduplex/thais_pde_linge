"""Demande d'inventaire periodique (linge de lit) envoyee au personnel, pour
ajuster la commande hebdomadaire via --stock. Lancee par cron le jeudi
(avant la livraison du vendredi et le rush du week-end), avec un delai
aleatoire pour ne pas arriver a heure fixe (voir run_inventory_request.sh).
"""

from __future__ import annotations

import argparse
import datetime
import os

import config as cfg
from linge_commande import build_inventory_request_html, send_notification_email


def should_send(state_path: str, today: datetime.date, *, interval_days: int) -> bool:
    """True s'il n'y a pas d'etat (jamais envoye) ou si l'intervalle minimal
    depuis le dernier envoi est ecoule."""

    try:
        with open(state_path, encoding="utf-8") as f:
            last_sent = datetime.date.fromisoformat(f.read().strip())
    except FileNotFoundError:
        return True
    return (today - last_sent).days >= interval_days


def record_sent(state_path: str, today: datetime.date) -> None:
    with open(state_path, "w", encoding="utf-8") as f:
        f.write(today.isoformat())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Demande d'inventaire linge de lit")
    parser.add_argument("--config", required=True, metavar="FICHIER", help="Config hotel/fournisseur (configs/*.json)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche le contenu sans envoyer")
    parser.add_argument("--state-file", metavar="FICHIER", help="Fichier memorisant la date du dernier envoi (rythme adaptatif)")
    parser.add_argument("--interval-days", type=int, default=21, help="Intervalle minimal entre deux demandes (defaut 21j = ~3 semaines)")
    parser.add_argument("--force", action="store_true", help="Ignore l'intervalle et envoie quand meme (pour un controle ponctuel supplementaire)")
    args = parser.parse_args(argv)

    hotel_config = cfg.load_config(args.config)
    html = build_inventory_request_html(hotel_config)

    if args.dry_run:
        print(html)
        return

    today = datetime.date.today()
    if args.state_file and not args.force and not should_send(args.state_file, today, interval_days=args.interval_days):
        print(f"Prochaine demande pas encore due (intervalle {args.interval_days}j) — envoi ignore.")
        return

    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_app_password = os.environ.get("SMTP_APP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_username)
    inventory_to = os.environ.get("INVENTORY_TO")
    if not smtp_username or not smtp_app_password or not inventory_to:
        parser.error("SMTP_USERNAME, SMTP_APP_PASSWORD et INVENTORY_TO sont requis dans l'environnement")

    subject = f"Inventaire linge de lit — {hotel_config.hotel_name}"
    send_notification_email(
        html,
        smtp_username=smtp_username,
        smtp_app_password=smtp_app_password,
        from_addr=smtp_from,
        to_addr=inventory_to,
        subject=subject,
    )
    print(f"Demande d'inventaire envoyee a {inventory_to} (from {smtp_from})")

    if args.state_file:
        record_sent(args.state_file, today)


if __name__ == "__main__":
    main()
