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


def test_select_group_returns_first_slice_and_next_cursor():
    codes = ["a", "b", "c", "d", "e", "f", "g"]

    selected, next_cursor = ir.select_group(codes, group_size=3, cursor=0)

    assert selected == ["a", "b", "c"]
    assert next_cursor == 3


def test_select_group_continues_from_cursor():
    codes = ["a", "b", "c", "d", "e", "f", "g"]

    selected, next_cursor = ir.select_group(codes, group_size=3, cursor=3)

    assert selected == ["d", "e", "f"]
    assert next_cursor == 6


def test_select_group_wraps_around_when_reaching_the_end():
    codes = ["a", "b", "c", "d", "e", "f", "g"]

    selected, next_cursor = ir.select_group(codes, group_size=3, cursor=6)

    assert selected == ["g", "a", "b"]
    assert next_cursor == 2


def test_select_group_handles_group_size_covering_everything():
    codes = ["a", "b", "c"]

    selected, next_cursor = ir.select_group(codes, group_size=10, cursor=0)

    assert selected == ["a", "b", "c"]
    assert next_cursor == 0


def test_load_cursor_defaults_to_zero_when_no_state_file(tmp_path):
    cursor_path = tmp_path / "cursor.txt"

    assert ir.load_cursor(str(cursor_path)) == 0


def test_save_and_load_cursor_roundtrip(tmp_path):
    cursor_path = tmp_path / "cursor.txt"

    ir.save_cursor(str(cursor_path), 5)

    assert ir.load_cursor(str(cursor_path)) == 5
