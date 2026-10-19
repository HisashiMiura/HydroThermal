import math
import os

import pandas as pd
import pytest


from modules.material_loaders import WHAMCAVITY_FILE, load_whamcavity, _liquid_diffusivity_from_ranges
from modules.material_props import NoLiquidDiffusivity


def test_load_whamcavity():
    """旧 Excel の19材料が、Excel と同じ順で読み込まれることを確認する。"""

    ms = load_whamcavity()

    names = pd.read_excel(WHAMCAVITY_FILE, sheet_name='material_prop')['name'].tolist()

    assert len(ms) == 19
    assert [m.name for m in ms] == names


def test_load_whamcavity_file_not_found(tmp_path):
    """ファイルがないとき、FileNotFoundError になることを確認する。"""

    with pytest.raises(FileNotFoundError):
        load_whamcavity(os.path.join(tmp_path, 'not_found.xlsx'))


def test_load_whamcavity_duplicate_name(tmp_path):
    """名前が重複しているとき、ValueError になることを確認する。

    旧 Excel の先頭の行を末尾にもう一度足した Excel を、一時フォルダ（tmp_path）に作って読む。
    """

    df = pd.read_excel(WHAMCAVITY_FILE, sheet_name='material_prop')
    df = pd.concat([df, df.iloc[[0]]])

    path = os.path.join(tmp_path, 'duplicate.xlsx')
    df.to_excel(path, sheet_name='material_prop', index=False)

    with pytest.raises(ValueError, match='重複'):
        load_whamcavity(path)


def test_liquid_diffusivity_from_ranges_0():
    """範囲分け数 0 のとき、「液水が移動しない」部品になることを確認する。

    No.4 MEWS Building Membrane IA の値（a は「測っていない」の印 ln(99999)）。
    """

    d = _liquid_diffusivity_from_ranges(0, [(None, 0, (math.log(99999), 0, 0, 0, 0, 0, 0))])

    assert isinstance(d, NoLiquidDiffusivity)
    assert d.d_w(0.1) == 0.0


@pytest.mark.parametrize('u', [0.0, 0.05, 0.2])
def test_liquid_diffusivity_from_ranges_1(u):
    """範囲分け数 1 のとき、区間1の式を含水率によらず使うことを確認する。

    No.14 MEWS Brick I - White Concrete Brick の値。Excel の上限は 0 だが使わないので、u > 0 でも式の値になる。
    """

    d = _liquid_diffusivity_from_ranges(1, [(None, 0, (-32.285, 272.18, 0, 0, 0, 0, 0))])

    assert d.d_w(u) == pytest.approx(math.exp(-32.285 + 272.18 * u), rel=1e-12)



# No.1 MEWS Aerated Concrete の値（範囲分け数 3）
_RANGES_NO1 = [
    (None, 0.087, (-18.55994281128587, 0, 0, 0, 0, 0, 0)),
    (0.087, 0.54, (-15.073, -63.312, 324.96, -731.86, 623.3, 0, 0)),
    (0.54, 1.3, (-16.772022118364983, 0, 0, 0, 0, 0, 0)),
]

# No.2 MEWS Oriented Strand Board の値（範囲分け数 2）。区間3 の欄は Excel では 0
_RANGES_NO2 = [
    (None, 0.92, (-18.023, -34.413, 140.32, -285.57, 277.28, -102.33, 0)),
    (0.92, 1.4, (-21.996231512759298, 0, 0, 0, 0, 0, 0)),
    (0, 0, (0, 0, 0, 0, 0, 0, 0)),
]


def _exp_poly(coefficients, u):
    """exp(a + b·u + c·u^2 + d·u^3 + e·u^4 + f·u^5 + g·u^6) を求める（テストの期待値用）。"""
    a, b, c, d, e, f, g = coefficients
    return math.exp(a + b * u + c * u**2 + d * u**3 + e * u**4 + f * u**5 + g * u**6)


@pytest.mark.parametrize('u, i', [
    (0.0, 0),    # 含水率 0 でも区間1（下限は −∞）
    (0.05, 0),
    (0.087, 0),  # 区間1と区間2の境目ちょうどは下側の区間1
    (0.3, 1),
    (0.54, 1),   # 区間2と区間3の境目ちょうどは下側の区間2
    (0.8, 2),
])
def test_liquid_diffusivity_from_ranges_3(u, i):
    """範囲分け数 3 のとき、含水率が入る区間の式を使うことを確認する（No.1 の値）。"""

    d = _liquid_diffusivity_from_ranges(3, _RANGES_NO1)

    assert d.d_w(u) == pytest.approx(_exp_poly(_RANGES_NO1[i][2], u), rel=1e-12)


@pytest.mark.parametrize('u, i', [
    (0.0, 0),
    (0.5, 0),
    (1.2, 1),
])
def test_liquid_diffusivity_from_ranges_2(u, i):
    """範囲分け数 2 のとき、区間1・2の式を使うことを確認する（No.2 の値）。"""

    d = _liquid_diffusivity_from_ranges(2, _RANGES_NO2)

    assert d.d_w(u) == pytest.approx(_exp_poly(_RANGES_NO2[i][2], u), rel=1e-12)


def test_liquid_diffusivity_from_ranges_2_ignores_range3():
    """範囲分け数 2 のとき、区間3 の欄の値は使わないことを確認する（No.2 の値）。"""

    d = _liquid_diffusivity_from_ranges(2, _RANGES_NO2)

    assert len(d.ranges) == 2


def test_liquid_diffusivity_from_ranges_not_implemented():
    """範囲分け数 4 のとき、まだ対応していないので NotImplementedError になることを確認する。"""

    with pytest.raises(NotImplementedError):
        _liquid_diffusivity_from_ranges(4, _RANGES_NO1)
