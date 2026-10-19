import math
import os

import openpyxl
import pytest


from modules.material_props import (
    FormulaIsotherm,
    PowerExpIsotherm,
    ConstantVaporConductivity,
    PowerExpVaporConductivity,
    NoLiquidDiffusivity,
    PiecewiseExpPolyDiffusivity,
)


def test_formula_isotherm_two_formulas():
    """式2本：境目を超えたら conditional の式、境目ちょうどは基本の式を使う。"""

    isotherm = FormulaIsotherm(formula='1', conditional=((0.5, '2'),))

    assert isotherm.u(0.3) == 1
    assert isotherm.u(0.5) == 1
    assert isotherm.u(0.7) == 2


def test_formula_isotherm_order():
    """式3本：conditional は前から順に調べ、最初に当てはまった式を使う。"""

    isotherm = FormulaIsotherm(formula='1', conditional=((0.9, '3'), (0.5, '2')))

    assert isotherm.u(0.3) == 1
    assert isotherm.u(0.7) == 2
    assert isotherm.u(0.95) == 3

    # 並べ方を逆にすると、0.9 を超えていても先に 0.5 の判定に当てはまる（シージングと同じ状況）
    isotherm = FormulaIsotherm(formula='1', conditional=((0.5, '2'), (0.9, '3')))

    assert isotherm.u(0.95) == 2


# No.1 MEWS Aerated Concrete の平衡含水率の係数（materials_mews_ashrae.xlsx）
_aerated_concrete_isotherm = {'a': 0.78743, 'b': 17.297, 'c': -0.35107, 'd': 78.553}


def test_power_exp_isotherm_at_saturation():
    """相対湿度 100%（x = 1）のとき、含水率が a になることを確認する。"""

    isotherm = PowerExpIsotherm(**_aerated_concrete_isotherm)

    assert isotherm.u(1.0) == 0.78743


def test_power_exp_isotherm_value():
    """式 u = a·x^b·exp(c·(1 − x^d)) をそのまま書いて計算した値と一致することを確認する。"""

    isotherm = PowerExpIsotherm(**_aerated_concrete_isotherm)

    for x in [0.5, 0.9, 0.98]:
        expected = 0.78743 * x**17.297 * math.exp(-0.35107 * (1 - x**78.553))
        assert isotherm.u(x) == expected, f'x={x}'


def test_power_exp_isotherm_at_zero():
    """相対湿度 0%（x = 0）のとき、含水率が 0 になることを確認する。"""

    isotherm = PowerExpIsotherm(**_aerated_concrete_isotherm)

    assert isotherm.u(0.0) == 0.0


# No.62 ASHRAE Low-density Glassfibre Batt Insulation の平衡含水率の係数（Parameter = 2）
_glassfibre_isotherm = {'a': 0.027903, 'b': 0.64024, 'c': -1.5875, 'd': 7.1897, 'f': 87, 'g': 0.022224100929699547}


def test_power_exp_isotherm_linear_below_x0():
    """Parameter = 2 の材料でも、x ≤ 0.98 では u = a·x^b·exp(c·(1 − x^d)) を使うことを確認する。

    x = 0.98 ちょうども、この式を使う（直線の式とは最後の桁が違うので見分けられる）。
    """

    isotherm = PowerExpIsotherm(**_glassfibre_isotherm)

    for x in [0.5, 0.9, 0.98]:
        expected = 0.027903 * x**0.64024 * math.exp(-1.5875 * (1 - x**7.1897))
        assert isotherm.u(x) == expected, f'x={x}'


def test_power_exp_isotherm_linear_at_saturation():
    """Parameter = 2 の材料で、相対湿度 100%（x = 1）のとき、含水率が f になることを確認する。"""

    isotherm = PowerExpIsotherm(**_glassfibre_isotherm)

    assert isotherm.u(1.0) == 87


def test_power_exp_isotherm_linear_middle():
    """Parameter = 2 の材料で、x = 0.99 のとき、直線のちょうど真ん中 (f + g) / 2 になることを確認する。

    0.99 − 0.98 がちょうど 0.01 にならず最後の桁がずれるため、pytest.approx で比べる。
    """

    isotherm = PowerExpIsotherm(**_glassfibre_isotherm)

    assert isotherm.u(0.99) == pytest.approx((87 + 0.022224100929699547) / 2, rel=1e-12)


def test_power_exp_isotherm_f_without_g():
    """f だけを指定したとき、ValueError になることを確認する。"""

    with pytest.raises(ValueError):
        PowerExpIsotherm(a=0.027903, b=0.64024, c=-1.5875, d=7.1897, f=87)


def test_constant_vapor_conductivity():
    """湿気伝導率が一定の部品は、相対湿度によらず与えた値を返すことを確認する。"""

    conductivity = ConstantVaporConductivity(value=2.61E-11)

    for x in [0.0, 0.3, 0.5, 0.9, 1.0]:
        assert conductivity.lambda_dsh_m(x) == 2.61E-11, f'x={x}'


# materials_mews_ashrae.xlsx（Excel が計算した値を読むため data_only=True で開く）
_wb_mews_ashrae = openpyxl.load_workbook(
    os.path.join(os.path.dirname(__file__), '..', 'modules', 'materials_mews_ashrae.xlsx'),
    data_only=True
)


def _read_mews_ashrae_vapor():
    """materials_mews_ashrae.xlsx から湿気伝導率の係数と、Excel が計算した値を読む。

    Returns:
        係数の辞書 {No: (a, b, c, d)}、
        相対湿度のリスト（0.0～1.0）、
        Excel が計算した値の辞書 {No: [各相対湿度での値]}
    """

    # 「データファイル用」シート：A列 No、G～J列 係数 a～d（3行目から）
    ws = _wb_mews_ashrae['データファイル用']
    coefficients = {
        ws.cell(row, 1).value: tuple(ws.cell(row, col).value for col in range(7, 11))
        for row in range(3, ws.max_row + 1)
        if ws.cell(row, 1).value is not None
    }

    # 「湿気伝導率」シート：2行目 相対湿度（G列から）、3行目から A列 No と G列以降 計算値
    # 84行目より下はグラフ表示用の別の表なので、No が数値の行だけを読む。
    ws = _wb_mews_ashrae['湿気伝導率']
    xs = [ws.cell(2, col).value for col in range(7, ws.max_column + 1)]
    expected = {}
    for row in range(3, ws.max_row + 1):
        no = ws.cell(row, 1).value
        if not isinstance(no, int):
            break
        expected[no] = [ws.cell(row, col).value for col in range(7, ws.max_column + 1)]

    return coefficients, xs, expected


_vapor_coefficients, _vapor_xs, _vapor_expected = _read_mews_ashrae_vapor()


@pytest.mark.parametrize('no', list(_vapor_expected.keys()))
def test_power_exp_vapor_conductivity_mews_ashrae(no):
    """新しい Excel の材料で、Excel が計算した湿気伝導率と同じ値になることを確認する。"""

    a, b, c, d = _vapor_coefficients[no]
    conductivity = PowerExpVaporConductivity(a=a, b=b, c=c, d=d)

    for x, expected in zip(_vapor_xs, _vapor_expected[no]):

        if expected == '#DIV/0!':
            # d が負の材料（No.28 Fibreboard II）は x = 0 で 0 の負の数乗になり、Excel でも計算できない。
            with pytest.raises(ZeroDivisionError):
                conductivity.lambda_dsh_m(x)
            continue

        # Excel と Python で計算の最後の桁がずれることがあるので、相対誤差 1e-9 で判定する。
        assert conductivity.lambda_dsh_m(x) == pytest.approx(expected, rel=1e-9, abs=0), f'x={x}'


def test_no_liquid_diffusivity():
    """液水が移動しない材料は、含水率によらず液水拡散係数が 0 になることを確認する。"""

    diffusivity = NoLiquidDiffusivity()

    for u in [0.0, 0.1, 0.5, 1.0, 2.0]:
        assert diffusivity.d_w(u) == 0.0, f'u={u}'


def test_piecewise_exp_poly_diffusivity_diff():
    """範囲の制限をしないとき、Fortran（Whamcavity.f95）の DIFF の拡散係数と同じ値になることを確認する。"""

    diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
        (-math.inf, math.inf, (-30.91, 4.2967, -0.22017, 0, 0, 0, 0)),
    ))

    # 0.00, 0.05, ..., 2.00
    for i in range(41):
        d1 = i * 0.05
        assert diffusivity.d_w(d1) == math.exp(-30.91 + 4.2967 * d1 - 0.22017 * (d1**2)), f'u={d1}'


def test_piecewise_exp_poly_diffusivity_all_terms():
    """a～g のすべての項が計算に使われることを確認する。"""

    diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
        (-math.inf, math.inf, (1, 2, 3, 4, 5, 6, 7)),
    ))

    # u = 0 のときは exp(a)
    assert diffusivity.d_w(0.0) == pytest.approx(math.exp(1))

    # u = 1 のときは exp(a + b + c + d + e + f + g)
    assert diffusivity.d_w(1.0) == pytest.approx(math.exp(28))

    # u = 0.5 のときは exp(1 + 2×0.5 + 3×0.5^2 + ... + 7×0.5^6)
    assert diffusivity.d_w(0.5) == pytest.approx(math.exp(sum((i + 1) * 0.5**i for i in range(7))))


def test_piecewise_exp_poly_diffusivity_plywood():
    """構造用合板1：含水率 0.45 を超え 1.10 以下のときだけ式で計算し、それ以外は 0 になることを確認する。"""

    diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
        (0.45, 1.10, (-30.91, 4.2967, -0.22017, 0, 0, 0, 0)),
    ))

    # 0.00, 0.05, ..., 2.00
    for i in range(41):
        d1 = i * 0.05
        if 0.45 < d1 <= 1.10:
            expected = math.exp(-30.91 + 4.2967 * d1 - 0.22017 * (d1**2))
        else:
            expected = 0.0
        assert diffusivity.d_w(d1) == expected, f'u={d1}'

    # 境目ちょうど：下限は範囲外、上限は範囲内
    assert diffusivity.d_w(0.45) == 0.0
    assert diffusivity.d_w(1.10) > 0.0


def test_piecewise_exp_poly_diffusivity_ranges():
    """3区間：含水率の区間ごとに正しい式が選ばれることを確認する。"""

    # 区間ごとに a だけを変えた一定値の式（exp(-20), exp(-19), exp(-18)）
    diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
        (-math.inf, 0.1, (-20, 0, 0, 0, 0, 0, 0)),
        (0.1, 0.5, (-19, 0, 0, 0, 0, 0, 0)),
        (0.5, 1.0, (-18, 0, 0, 0, 0, 0, 0)),
    ))

    assert diffusivity.d_w(0.0) == math.exp(-20)
    assert diffusivity.d_w(0.3) == math.exp(-19)
    assert diffusivity.d_w(0.7) == math.exp(-18)

    # 境目ちょうどは下側の区間に入る
    assert diffusivity.d_w(0.1) == math.exp(-20)
    assert diffusivity.d_w(0.5) == math.exp(-19)
    assert diffusivity.d_w(1.0) == math.exp(-18)

    # 最後の区間の上限を超えたら 0
    assert diffusivity.d_w(1.2) == 0.0


def test_piecewise_exp_poly_diffusivity_gap():
    """区間の間にすき間があるとき、すき間の含水率では 0 になることを確認する。"""

    diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
        (-math.inf, 0.1, (-20, 0, 0, 0, 0, 0, 0)),
        (0.2, 1.0, (-19, 0, 0, 0, 0, 0, 0)),
    ))

    assert diffusivity.d_w(0.05) == math.exp(-20)
    assert diffusivity.d_w(0.15) == 0.0
    assert diffusivity.d_w(0.5) == math.exp(-19)


def test_piecewise_exp_poly_diffusivity_wrong_length():
    """係数が7個でないときはエラーになることを確認する。"""

    with pytest.raises(ValueError):
        PiecewiseExpPolyDiffusivity(ranges=(
            (0.45, 1.10, (-30.91, 4.2967, -0.22017)),
        ))


def test_piecewise_exp_poly_diffusivity_wrong_range():
    """下限が上限以上のときはエラーになることを確認する。"""

    with pytest.raises(ValueError):
        PiecewiseExpPolyDiffusivity(ranges=(
            (0.5, 0.1, (-20, 0, 0, 0, 0, 0, 0)),
        ))
