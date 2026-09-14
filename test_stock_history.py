import datetime

import stock_history as sh


def test_append_history_creates_file_with_header_and_rows(tmp_path):
    history_path = tmp_path / "history.csv"

    sh.append_history(str(history_path), datetime.date(2026, 9, 14), {"2941": 40, "1341": 30})

    lines = history_path.read_text().strip().splitlines()
    assert lines[0] == "date;code;quantite"
    assert "2026-09-14;2941;40" in lines
    assert "2026-09-14;1341;30" in lines


def test_append_history_appends_to_existing_file_without_duplicating_header(tmp_path):
    history_path = tmp_path / "history.csv"
    sh.append_history(str(history_path), datetime.date(2026, 9, 14), {"2941": 40})

    sh.append_history(str(history_path), datetime.date(2026, 10, 5), {"2941": 35})

    lines = history_path.read_text().strip().splitlines()
    assert lines.count("date;code;quantite") == 1
    assert "2026-09-14;2941;40" in lines
    assert "2026-10-05;2941;35" in lines


def test_read_stock_returns_empty_dict_when_file_missing(tmp_path):
    stock_path = tmp_path / "stock.csv"

    assert sh.read_stock(str(stock_path)) == {}


def test_write_then_read_stock_roundtrip(tmp_path):
    stock_path = tmp_path / "stock.csv"

    sh.write_stock(str(stock_path), {"2941": 40, "1341": 30})
    result = sh.read_stock(str(stock_path))

    assert result == {"2941": 40, "1341": 30}


def test_merge_stock_updates_only_counted_references_and_keeps_the_rest(tmp_path):
    stock_path = tmp_path / "stock.csv"
    sh.write_stock(str(stock_path), {"2941": 40, "1341": 30, "11143": 20})

    merged = sh.merge_stock(str(stock_path), {"2941": 35})

    assert merged == {"2941": 35, "1341": 30, "11143": 20}
    assert sh.read_stock(str(stock_path)) == merged


def test_record_inventory_reply_appends_history_and_merges_stock(tmp_path):
    history_path = tmp_path / "history.csv"
    stock_path = tmp_path / "stock.csv"
    sh.write_stock(str(stock_path), {"2941": 40, "1341": 30})

    sh.record_inventory_reply(
        str(history_path), str(stock_path), datetime.date(2026, 10, 5), {"2941": 33}
    )

    assert sh.read_stock(str(stock_path)) == {"2941": 33, "1341": 30}
    assert "2026-10-05;2941;33" in history_path.read_text()
