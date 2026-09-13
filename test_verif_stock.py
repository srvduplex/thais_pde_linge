import datetime

import verif_stock as vs


def test_active_friday_for_a_monday_is_last_fridays_date():
    # Lundi 14/09 -> la fenetre en cours a commence le vendredi 11/09
    assert vs.active_friday(datetime.date(2026, 9, 14)) == datetime.date(2026, 9, 11)


def test_active_friday_for_friday_itself_is_that_day():
    assert vs.active_friday(datetime.date(2026, 9, 18)) == datetime.date(2026, 9, 18)


def test_active_friday_for_thursday_is_the_friday_six_days_before():
    assert vs.active_friday(datetime.date(2026, 9, 17)) == datetime.date(2026, 9, 11)


def test_delta_report_flags_reference_exceeding_safety_stock():
    snapshot = {"2941": 35, "8786": 53}
    current = {"2941": 44, "8786": 53}  # 2941: +9 depuis la commande, +0 pour 8786

    report = vs.compute_delta_report(snapshot, current, safety_stock_pct=0.20)

    # 20% de 35 = 7 (tronque) ; delta 9 > 7 -> a risque, topup suggere = 9-7 = 2
    assert report["2941"]["ordered"] == 35
    assert report["2941"]["current"] == 44
    assert report["2941"]["delta"] == 9
    assert report["2941"]["safety_stock"] == 7
    assert report["2941"]["at_risk"] is True
    assert report["2941"]["suggested_topup"] == 2


def test_delta_report_does_not_flag_reference_within_safety_stock():
    snapshot = {"2941": 35}
    current = {"2941": 40}  # delta = 5, safety stock 20% de 35 = 7 -> absorbe

    report = vs.compute_delta_report(snapshot, current, safety_stock_pct=0.20)

    assert report["2941"]["delta"] == 5
    assert report["2941"]["safety_stock"] == 7
    assert report["2941"]["at_risk"] is False
    assert report["2941"]["suggested_topup"] == 0


def test_delta_report_ignores_references_with_no_increase():
    snapshot = {"2941": 35, "8787": 41}
    current = {"2941": 30, "8787": 41}  # baisse (annulation) et stable

    report = vs.compute_delta_report(snapshot, current, safety_stock_pct=0.20)

    assert report["2941"]["at_risk"] is False
    assert report["2941"]["suggested_topup"] == 0
    assert report["8787"]["at_risk"] is False


def test_any_at_risk_detects_whether_a_report_needs_an_alert():
    ras_report = {"2941": {"at_risk": False}, "8786": {"at_risk": False}}
    alert_report = {"2941": {"at_risk": False}, "8786": {"at_risk": True}}

    assert vs.any_at_risk(ras_report) is False
    assert vs.any_at_risk(alert_report) is True


def test_build_status_email_html_shows_ras_when_nothing_at_risk():
    report = {"2941": {"ordered": 35, "current": 36, "delta": 1, "safety_stock": 7, "at_risk": False, "suggested_topup": 0}}

    html = vs.build_status_email_html(report, window_from="2026-09-18", window_to="2026-09-24")

    assert "RAS" in html
    assert "2941" not in html  # pas de detail affiche quand tout va bien


def test_build_status_email_html_lists_at_risk_references():
    report = {
        "2941": {"ordered": 35, "current": 44, "delta": 9, "safety_stock": 7, "at_risk": True, "suggested_topup": 2},
        "8787": {"ordered": 41, "current": 41, "delta": 0, "safety_stock": 8, "at_risk": False, "suggested_topup": 0},
    }

    html = vs.build_status_email_html(report, window_from="2026-09-18", window_to="2026-09-24")

    assert "2941" in html
    assert "Drap Clas blc l. noir 280 NF" in html
    assert "8787" not in html  # seule la reference a risque est detaillee
