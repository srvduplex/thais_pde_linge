import datetime
import os

import inventory_request as ir


def test_should_send_when_no_state_file_exists(tmp_path):
    state_path = tmp_path / "last_sent.txt"

    assert ir.should_send(str(state_path), datetime.date(2026, 9, 17), interval_days=21) is True


def test_should_not_send_before_interval_elapsed(tmp_path):
    state_path = tmp_path / "last_sent.txt"
    state_path.write_text("2026-09-10")

    # 7 jours plus tard seulement, intervalle de 21 jours -> pas encore
    assert ir.should_send(str(state_path), datetime.date(2026, 9, 17), interval_days=21) is False


def test_should_send_once_interval_elapsed(tmp_path):
    state_path = tmp_path / "last_sent.txt"
    state_path.write_text("2026-09-10")

    assert ir.should_send(str(state_path), datetime.date(2026, 10, 1), interval_days=21) is True


def test_record_sent_writes_the_date(tmp_path):
    state_path = tmp_path / "last_sent.txt"

    ir.record_sent(str(state_path), datetime.date(2026, 9, 17))

    assert state_path.read_text().strip() == "2026-09-17"
