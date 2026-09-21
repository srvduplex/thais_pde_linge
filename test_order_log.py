import datetime

import order_log as ol


def test_compute_order_number_uses_iso_week_and_hotel_code():
    # 2026-09-25 est en semaine ISO 39
    assert ol.compute_order_number(datetime.date(2026, 9, 25), "PDE") == "39/PDE"


def test_has_already_sent_false_when_log_missing(tmp_path):
    log_path = tmp_path / "order_log.jsonl"

    assert ol.has_already_sent(str(log_path), "2026-09-25", "2026-10-01") is False


def test_has_already_sent_true_for_matching_window(tmp_path):
    log_path = tmp_path / "order_log.jsonl"
    ol.record_sent_order(
        str(log_path),
        order_number="39/PDE",
        date_sent="2026-09-21T05:00:02Z",
        from_date="2026-09-25",
        to_date="2026-10-01",
        to_email="pauline.padovan@elis.com",
        cc_email="contact@platdetain.fr",
        quantities={"2941": 20},
    )

    assert ol.has_already_sent(str(log_path), "2026-09-25", "2026-10-01") is True
    assert ol.has_already_sent(str(log_path), "2026-10-02", "2026-10-08") is False


def test_record_sent_order_appends_without_overwriting(tmp_path):
    log_path = tmp_path / "order_log.jsonl"
    ol.record_sent_order(
        str(log_path), order_number="38/PDE", date_sent="2026-09-14T05:00:00Z",
        from_date="2026-09-18", to_date="2026-09-24",
        to_email="a@example.com", cc_email=None, quantities={"1341": 6},
    )
    ol.record_sent_order(
        str(log_path), order_number="39/PDE", date_sent="2026-09-21T05:00:02Z",
        from_date="2026-09-25", to_date="2026-10-01",
        to_email="a@example.com", cc_email=None, quantities={"1341": 20},
    )

    entries = ol.read_log(str(log_path))
    assert len(entries) == 2
    assert entries[0]["order_number"] == "38/PDE"
    assert entries[1]["order_number"] == "39/PDE"
    assert entries[1]["quantities"] == {"1341": 20}
