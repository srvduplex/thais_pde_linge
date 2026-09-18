"""Enregistrement des reponses d'inventaire : historique horodate (pour
calculer des ecarts entre comptages une fois qu'on aura plusieurs points de
donnees) et mise a jour du stock courant utilise par --stock.
"""

from __future__ import annotations

import csv
import datetime
import json
import os


def append_history(history_path: str, date: datetime.date, quantities: dict) -> None:
    """Ajoute une ligne par reference comptee a l'historique (cree le fichier
    avec en-tete s'il n'existe pas encore)."""

    file_exists = os.path.exists(history_path)
    with open(history_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        if not file_exists:
            writer.writerow(["date", "code", "quantite"])
        for code, qty in quantities.items():
            writer.writerow([date.isoformat(), code, qty])


def read_stock(stock_path: str) -> dict:
    if not os.path.exists(stock_path):
        return {}
    result = {}
    with open(stock_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if not row:
                continue
            code, value = row[0].strip(), row[1].strip()
            if code.lower() == "code":
                continue
            result[code] = int(value)
    return result


def write_stock(stock_path: str, quantities: dict) -> None:
    with open(stock_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        writer.writerow(["code", "quantite"])
        for code, qty in quantities.items():
            writer.writerow([code, qty])


def merge_stock(stock_path: str, quantities: dict) -> dict:
    """Met a jour uniquement les references presentes dans `quantities`,
    conserve les autres telles quelles (utile pour un inventaire partiel /
    en rotation)."""

    current = read_stock(stock_path)
    current.update(quantities)
    write_stock(stock_path, current)
    return current


def load_carryover(carryover_path: str) -> dict:
    """Dernier ecart connu (current - commande) par reference, calcule par la
    verification nocturne. Positif = manque a ajouter, negatif = surplus a
    deduire, pour ramener le stock au meme niveau cible chaque semaine."""

    if not os.path.exists(carryover_path):
        return {}
    with open(carryover_path, encoding="utf-8") as f:
        return json.load(f)


def save_carryover(carryover_path: str, deltas: dict) -> None:
    with open(carryover_path, "w", encoding="utf-8") as f:
        json.dump(deltas, f, indent=2, ensure_ascii=False)


def record_inventory_reply(
    history_path: str, stock_path: str, date: datetime.date, quantities: dict
) -> dict:
    """Enregistre une reponse d'inventaire : ajoute a l'historique ET met a
    jour le stock courant. Renvoie le stock complet apres fusion."""

    append_history(history_path, date, quantities)
    return merge_stock(stock_path, quantities)
