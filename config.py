"""Chargement de la configuration par hotel/fournisseur (referentiel d'articles,
dotation de literie, coordonnees) — voir configs/*.json. Le moteur de calcul
(linge_commande.py, verif_stock.py) est partage entre tous les hotels ; seule
cette configuration change d'un etablissement a l'autre.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class HotelConfig:
    hotel_name: str
    base_url: str
    label_to_categorie: dict
    room_label_to_categorie: dict
    referentiel: dict
    dotation_lit: dict
    tapis_par_categorie: dict
    taies_fixes: dict
    bed_linen_codes_lit90: set
    extra_bed_threshold: int | None
    extra_bed_dotation: dict
    minimum_order_qty: int
    footer_note: str
    signature: str
    supplier_name: str
    supplier_to_email: str


def load_config(path: str) -> HotelConfig:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return HotelConfig(
        hotel_name=data["hotel_name"],
        base_url=data["base_url"],
        label_to_categorie=data["label_to_categorie"],
        room_label_to_categorie=data.get("room_label_to_categorie", {}),
        referentiel=data["referentiel"],
        dotation_lit=data["dotation_lit"],
        tapis_par_categorie=data["tapis_par_categorie"],
        taies_fixes=data["taies_fixes"],
        bed_linen_codes_lit90=set(data["bed_linen_codes_lit90"]),
        extra_bed_threshold=data.get("extra_bed_threshold"),
        extra_bed_dotation=data.get("extra_bed_dotation", {}),
        minimum_order_qty=data.get("minimum_order_qty", 0),
        footer_note=data["footer_note"],
        signature=data["signature"],
        supplier_name=data["supplier_name"],
        supplier_to_email=data["supplier_to_email"],
    )
