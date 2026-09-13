import datetime
import json
import os

import config as cfg
import linge_commande as lc

FIXTURE_BOOKINGS = os.path.join(os.path.dirname(__file__), "fixtures", "bookings_semaine.json")
ELIS_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "plat_detain_elis.json")

CONFIG = cfg.load_config(ELIS_CONFIG_PATH)


def _booking(start_at, end_at, categorie_label, adults=2, children=0, canceled=False, no_show=False):
    return {
        "start_at": start_at,
        "end_at": end_at,
        "canceled": canceled,
        "no_show": no_show,
        "booking_rooms": [
            {
                "nb_persons": {"adults": adults, "children": children, "infants": 0},
                "room": {"room_type": {"label": categorie_label}},
            }
        ],
    }


def test_stay_night_kind_follows_2_and_4_day_cycle():
    kinds = [lc.stay_night_kind(day) for day in range(1, 9)]

    assert kinds == ["full", "none", "partial", "none", "full", "none", "partial", "none"]


def test_single_night_stay_is_a_full_change():
    bookings = [_booking("2026-09-13", "2026-09-14", "Chambre Double Supérieur", adults=2)]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG
    )

    assert qty["2941"] == 1  # drap 280
    assert qty["32830"] == 1  # housse marron
    assert qty["43128"] == 2  # taies 65x65 fixes (2), quelle que soit l'occupation
    assert qty["517"] == 2  # taies 50x80 fixes (2)
    assert qty["8786"] == 2  # drap bain = nb occupants (2)
    assert qty["8785"] == 2  # serviette = nb occupants (2)
    assert qty["8787"] == 1  # tapis (dotation double = 1)


def test_three_night_stay_has_one_partial_night_and_no_bed_linen_on_it():
    # nuit 1 = arrivee (full), nuit 2 = aucun changement, nuit 3 = partiel (serviette+tapis)
    bookings = [_booking("2026-09-13", "2026-09-16", "Chambre Double Supérieur", adults=1)]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG
    )

    assert qty["2941"] == 1  # drap 280 : uniquement nuit 1 (mise a blanc)
    assert qty["32830"] == 1
    assert qty["43128"] == 2  # taies : uniquement nuit 1
    assert qty["517"] == 2
    assert qty["8786"] == 2  # drap bain (= grande serviette) : nuit 1 (1) + nuit 3 (1)
    assert qty["8785"] == 2  # serviette : nuit 1 (1) + nuit 3 (1)
    assert qty["8787"] == 2  # tapis : nuit 1 (1) + nuit 3 (1)


def test_canceled_and_no_show_bookings_are_excluded():
    bookings = [
        _booking("2026-09-13", "2026-09-14", "Chambre Double Supérieur", canceled=True),
        _booking("2026-09-13", "2026-09-14", "Chambre Double Supérieur", no_show=True),
    ]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG
    )

    assert qty["2941"] == 0


def test_nights_outside_the_reporting_window_are_ignored():
    # Le sejour deborde avant la fenetre : seule la nuit du 13 doit compter.
    bookings = [_booking("2026-09-11", "2026-09-14", "Chambre Double Supérieur", adults=2)]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG
    )

    # jour de sejour au 13/09 = (13-11).days + 1 = 3 -> nuit partielle
    assert qty["2941"] == 0  # pas de changement de lit une nuit partielle
    assert qty["8785"] == 2  # serviette (occupants) sur la nuit partielle
    assert qty["8786"] == 2  # drap bain (grande serviette, meme cycle 2 jours)
    assert qty["8787"] == 1  # tapis (categorie double)


def test_unmapped_room_category_is_skipped_without_crashing():
    bookings = [_booking("2026-09-13", "2026-09-14", "Categorie inconnue", adults=2)]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG
    )

    assert all(value == 0 for value in qty.values())


def test_triple_sans_90_removes_lit90_bed_linen_only_on_full_nights():
    bookings = [_booking("2026-09-13", "2026-09-14", "Chambre Triple", adults=3)]

    qty = lc.compute_needs_from_bookings(
        bookings,
        datetime.date(2026, 9, 13),
        datetime.date(2026, 9, 19),
        CONFIG,
        triple_sans_90=True,
    )

    assert qty["1341"] == 0  # drap 180 du lit 90 exclu
    assert qty["41113"] == 0  # housse anis du lit 90 exclue
    assert qty["11143"] == 1  # lit 160 conserve
    assert qty["43128"] == 2  # taies fixes toujours presentes


def test_sans_bain_zeroes_bathroom_articles_but_keeps_bed_linen():
    bookings = [_booking("2026-09-13", "2026-09-14", "Chambre Double Supérieur", adults=2)]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG, sans_bain=True
    )

    assert qty["8786"] == 0
    assert qty["8785"] == 0
    assert qty["8787"] == 0
    assert qty["2941"] == 1


def test_sans_tapis_zeroes_only_tapis():
    bookings = [_booking("2026-09-13", "2026-09-14", "Chambre Double Supérieur", adults=2)]

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG, sans_tapis=True
    )

    assert qty["8787"] == 0
    assert qty["8786"] == 2


def test_reference_week_matches_real_thais_export():
    with open(FIXTURE_BOOKINGS, encoding="utf-8") as f:
        bookings = json.load(f)

    qty = lc.compute_needs_from_bookings(
        bookings, datetime.date(2026, 9, 13), datetime.date(2026, 9, 19), CONFIG
    )

    assert qty["2941"] == 26  # drap 280
    assert qty["11143"] == 2  # drap 310
    assert qty["1341"] == 2  # drap 180 (issu des Triple uniquement, 0 Twin)
    assert qty["32830"] == 26  # housse marron
    assert qty["41115"] == 2  # housse bleu marine
    assert qty["41113"] == 2  # housse anis
    assert qty["43128"] == 56  # taies 65x65
    assert qty["517"] == 56  # taies 50x80
    assert qty["8786"] == 53  # drap bain (grande serviette, cycle 2 jours comme la serviette)
    assert qty["8785"] == 53  # serviette eponge
    assert qty["8787"] == 34  # tapis bain


def test_apply_stock_subtracts_and_floors_at_zero(tmp_path):
    stock_path = tmp_path / "stock.csv"
    stock_path.write_text("code;quantite\n2941;10\n8787;100\n")

    qty = {"2941": 35, "8787": 41, "517": 64}
    result = lc.apply_stock(qty, str(stock_path))

    assert result["2941"] == 25
    assert result["8787"] == 0  # stock superieur au besoin -> plafonne a 0
    assert result["517"] == 64  # pas de stock compte pour cette reference -> inchange


def test_build_recap_table_uses_designations_from_config():
    qty = {"2941": 5}

    table = lc.build_recap_table(qty, CONFIG)

    assert "Drap Clas blc l. noir 280 NF" in table


def test_build_email_html_uses_footer_and_signature_from_config():
    qty = {"2941": 5}

    html = lc.build_email_html(qty, CONFIG)

    assert "Compte HT2 n° 244968" in html
    assert "Mathieu Tarrade" in html
