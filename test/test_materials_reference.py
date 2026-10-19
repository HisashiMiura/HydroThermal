import csv

import pytest


from test.make_materials_reference import REFERENCE_FILE, COLUMNS, calculate_rows


def _read_reference() -> dict:
    """基準値ファイルを読み込む。

    Returns:
        {(材料名, 相対湿度): {列名: 値}}
    """

    with open(REFERENCE_FILE, encoding='utf-8', newline='') as f:
        return {
            (row['name'], int(row['rh'])): {c: float(row[c]) for c in COLUMNS[2:]}
            for row in csv.DictReader(f)
        }


_reference = _read_reference()
_rows = calculate_rows()


def test_reference_covers_all():
    """基準値ファイルと今の計算結果で、材料と相対湿度の組み合わせが同じであることを確認する。"""

    assert set(_reference.keys()) == {(row['name'], row['rh']) for row in _rows}


@pytest.mark.parametrize('column', COLUMNS[2:])
def test_matches_reference(column):
    """今の Material の計算結果が、基準値と一致することを確認する。

    PC や Python のバージョンによって最後の数桁が変わるため、相対誤差 1e-12 まで許す。
    """

    for row in _rows:
        expected = _reference[(row['name'], row['rh'])][column]
        assert row[column] == pytest.approx(expected, rel=1e-12), f"{row['name']}, RH={row['rh']}%"
