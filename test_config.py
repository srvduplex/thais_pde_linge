import json

import config as cfg


def test_load_config_reads_json_into_a_config_object(tmp_path):
    config_path = tmp_path / "hotel.json"
    config_path.write_text(json.dumps({
        "hotel_name": "Hotel Test",
        "base_url": "https://test.thais-hotel.com",
        "label_to_categorie": {"Chambre Double": "double"},
        "referentiel": {
            "1000": {"designation": "Drap test", "dimension": "-", "liseret": "-", "section": "lit"},
        },
        "dotation_lit": {"double": {"1000": 1}},
        "tapis_par_categorie": {"double": 1},
        "taies_fixes": {},
        "bed_linen_codes_lit90": [],
        "footer_note": "Compte test",
        "signature": "Signature test",
        "supplier_name": "Fournisseur Test",
        "supplier_to_email": "contact@fournisseur-test.com",
    }))

    hotel_config = cfg.load_config(str(config_path))

    assert hotel_config.hotel_name == "Hotel Test"
    assert hotel_config.base_url == "https://test.thais-hotel.com"
    assert hotel_config.label_to_categorie == {"Chambre Double": "double"}
    assert hotel_config.room_label_to_categorie == {}  # absent du JSON -> defaut vide
    assert hotel_config.referentiel["1000"]["designation"] == "Drap test"
    assert hotel_config.dotation_lit == {"double": {"1000": 1}}
    assert hotel_config.tapis_par_categorie == {"double": 1}
    assert hotel_config.bed_linen_codes_lit90 == set()
    assert hotel_config.footer_note == "Compte test"
    assert hotel_config.signature == "Signature test"
    assert hotel_config.supplier_name == "Fournisseur Test"
    assert hotel_config.supplier_to_email == "contact@fournisseur-test.com"


def test_load_config_converts_bed_linen_codes_lit90_to_a_set(tmp_path):
    config_path = tmp_path / "hotel.json"
    config_path.write_text(json.dumps({
        "hotel_name": "Hotel Test",
        "base_url": "https://test.thais-hotel.com",
        "label_to_categorie": {},
        "referentiel": {},
        "dotation_lit": {},
        "tapis_par_categorie": {},
        "taies_fixes": {},
        "bed_linen_codes_lit90": ["1341", "41113"],
        "footer_note": "",
        "signature": "",
        "supplier_name": "",
        "supplier_to_email": "x@example.com",
    }))

    hotel_config = cfg.load_config(str(config_path))

    assert hotel_config.bed_linen_codes_lit90 == {"1341", "41113"}


def test_load_config_reads_explicit_room_label_to_categorie_override(tmp_path):
    config_path = tmp_path / "hotel.json"
    config_path.write_text(json.dumps({
        "hotel_name": "Hotel Test",
        "base_url": "https://test.thais-hotel.com",
        "label_to_categorie": {},
        "room_label_to_categorie": {"Chambre 5": "double", "Chambre 6": "twin"},
        "referentiel": {},
        "dotation_lit": {},
        "tapis_par_categorie": {},
        "taies_fixes": {},
        "bed_linen_codes_lit90": [],
        "footer_note": "",
        "signature": "",
        "supplier_name": "",
        "supplier_to_email": "x@example.com",
    }))

    hotel_config = cfg.load_config(str(config_path))

    assert hotel_config.room_label_to_categorie == {"Chambre 5": "double", "Chambre 6": "twin"}
