"""Log des commandes envoyees aux fournisseurs (linge) : garde-fou contre les
doublons (cf. incident du 21/09/2026 ou un test manuel + le cron reel ont
tous deux envoye la commande de la meme semaine a Elis) et base pour un
controle de facturation ulterieur (ref/qte par semaine, a rapprocher des
factures fournisseur recues par email).
"""

from __future__ import annotations

import json
import os


def compute_order_number(date_from, hotel_code: str) -> str:
    """Numero de commande lisible : <semaine ISO du debut de fenetre>/<code hotel>."""

    week = date_from.isocalendar()[1]
    return f"{week}/{hotel_code}"


def read_log(log_path: str) -> list:
    if not os.path.exists(log_path):
        return []
    entries = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def has_already_sent(log_path: str, from_date: str, to_date: str) -> bool:
    """True si une commande a deja ete enregistree pour exactement cette
    fenetre [from_date, to_date] (garde-fou anti-doublon)."""

    for entry in read_log(log_path):
        if entry["from_date"] == from_date and entry["to_date"] == to_date:
            return True
    return False


def record_sent_order(
    log_path: str,
    *,
    order_number: str,
    date_sent: str,
    from_date: str,
    to_date: str,
    to_email: str,
    cc_email: str = None,
    quantities: dict,
) -> None:
    entry = {
        "order_number": order_number,
        "date_sent": date_sent,
        "from_date": from_date,
        "to_date": to_date,
        "to_email": to_email,
        "cc_email": cc_email,
        "quantities": quantities,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
