import math

import pytest


from modules import thermo_dynamics
from modules.materials import Materials
from modules.material_loaders import load_whamcavity
from modules.material_props import (
    FormulaIsotherm,
    ConstantVaporConductivity,
    PowerExpVaporConductivity,
    NoLiquidDiffusivity,
    PiecewiseExpPolyDiffusivity,
)
from test.make_materials_reference import RHS, read_reference


_materials = Materials(load_whamcavity())

# 基準値（作り直す前の Material の計算結果）
_reference = read_reference()

# 確認する相対湿度, %（基準値ファイルと同じ。0% は軽量モルタルの式が計算できないため含まない）
_rhs = RHS


def test_load():

    ms = Materials(load_whamcavity())

    m = ms.get_material('シージング')

    assert m.lambda_h == 0.0586
    assert m.vapor_conductivity.value == 2.61E-11
    assert m.c == 0.0
    assert m.rho == 0.0


def test_get_material_not_found():
    """ない名前を指定したとき、KeyError になることを確認する。"""

    with pytest.raises(KeyError):
        _materials.get_material('ない材料')


def test_get_material_duplicate():
    """同じ名前の材料が2つあるとき、ValueError になることを確認する。"""

    ms = load_whamcavity()
    materials = Materials(ms + ms[:1])

    with pytest.raises(ValueError, match=ms[0].name):
        materials.get_material(ms[0].name)


@pytest.mark.parametrize('name', _materials.get_material_name())
def test_isotherm(name):
    """平衡含水率の部品が入っていて、基準値と同じ含水率になることを確認する。"""

    m = _materials.get_material(name)

    assert isinstance(m.isotherm, FormulaIsotherm)

    for rh in _rhs:
        expected = _reference[(name, rh)]['u']
        assert m.isotherm.u(rh * 0.01) == pytest.approx(expected, rel=1e-12), f'RH={rh}%'


def _fortran_sheathing_u(rh: float) -> float:
    """シージングの平衡含水率, kg/kg。Fortran（Whamcavity.f95 の SUBROUTINE AHGANS の 11 番）を書き写したもの。

    Fortran の式は含水率を %（wt%）で返すので、100 で割って kg/kg にする。

    Args:
        rh: 相対湿度, %
    """

    if rh <= 89:
        wd = -math.log(1 - .01 * rh) / .1612944
    elif rh < 95:
        wd = 639.22 - 14.988 * rh + .08943 * rh * rh
    else:
        wd = 2.446 * rh - 209.9

    return wd / 100


@pytest.mark.parametrize('rh', [1, 30, 50, 80, 89, 89.5, 92, 94.9, 95.1, 97, 99, 99.5])
def test_isotherm_sheathing_fortran(rh):
    """シージングの平衡含水率が、Fortran の式を kg/kg に直した値と一致することを確認する。

    RH 95% ちょうどは、Fortran は直線、Python は 2 次式を使う（境目の扱いの違い。値の差は 0.02%）ので含めない。
    """

    m = _materials.get_material('シージング')

    assert m.get_u(rh) == pytest.approx(_fortran_sheathing_u(rh), rel=1e-12)


def _fortran_glass_wool_u(rh: float) -> float:
    """グラスウール系の平衡含水率, kg/kg。Fortran（Whamcavity.f95 の SUBROUTINE AHGANS の 13 番）を書き写したもの。

    Fortran は最後に WD = D3*100. で % にしているので、その手前の D3（kg/kg）を返す。

    Args:
        rh: 相対湿度, %
    """

    d1 = rh * .01
    d2 = math.exp(-1.3016 * (1 - d1**101.667))
    d3 = 0.16 * d2 * d1**7.6448
    if d1 > 0.98:
        d3 = 47.79595 * d1 - 46.79595

    return d3


# Fortran で AHGANS の 13 番（グラスウール）の式を使う 6 材料
_GLASS_WOOL_GROUP = ['グラスウール1', 'セルロースファイバー', '発泡プラスチック1', '発泡プラスチック2', '発泡プラスチック3', 'グラスウール2']


@pytest.mark.parametrize('name', _GLASS_WOOL_GROUP)
@pytest.mark.parametrize('rh', [1, 50, 90, 97, 98, 98.5, 99, 99.5, 100])
def test_isotherm_glass_wool_fortran(name, rh):
    """グラスウール系 6 材料の平衡含水率が、Fortran の式と一致することを確認する（RH 98% を超えると直線）。"""

    m = _materials.get_material(name)

    assert m.get_u(rh) == pytest.approx(_fortran_glass_wool_u(rh), rel=1e-12)


@pytest.mark.parametrize('name', _materials.get_material_name())
def test_vapor_conductivity(name):
    """湿気伝導率の部品が入っていて、基準値と同じ値になることを確認する。"""

    m = _materials.get_material(name)

    if name == '構造用合板1':
        assert isinstance(m.vapor_conductivity, PowerExpVaporConductivity)
    else:
        assert isinstance(m.vapor_conductivity, ConstantVaporConductivity)

    for rh in _rhs:
        expected = _reference[(name, rh)]['lambda_dsh_m']
        assert m.vapor_conductivity.lambda_dsh_m(rh * 0.01) == pytest.approx(expected, rel=1e-12), f'RH={rh}%'


@pytest.mark.parametrize('name', _materials.get_material_name())
def test_liquid_diffusivity(name):
    """液水拡散係数の部品が入っていることを確認する。

    構造用合板1 は含水率 0.45 を超え 1.10 以下で 0 より大きく、範囲外で 0。ほかの材料は常に 0。
    """

    m = _materials.get_material(name)

    if name == '構造用合板1':
        assert isinstance(m.liquid_diffusivity, PiecewiseExpPolyDiffusivity)
        assert m.liquid_diffusivity.d_w(0.3) == 0.0
        assert m.liquid_diffusivity.d_w(0.45) == 0.0
        assert m.liquid_diffusivity.d_w(0.6) > 0.0
        assert m.liquid_diffusivity.d_w(1.10) > 0.0
        assert m.liquid_diffusivity.d_w(1.5) == 0.0
    else:
        assert isinstance(m.liquid_diffusivity, NoLiquidDiffusivity)
        for u in [0.0, 0.3, 0.6, 1.5]:
            assert m.liquid_diffusivity.d_w(u) == 0.0, f'u={u}'


def _fortran_diff(m, rh: float, t: float) -> float:
    """Fortran（Whamcavity.f95）の SUBROUTINE DIFF を、含水率を % で扱う元の形のまま書き写したもの。

    Fortran では、構造用合板1（材料番号5）で RH 90% を超えるときだけ DIFF を呼び、それ以外は 0 としていた。
    """

    if not (m.name == '構造用合板1' and rh > 90.0):
        return 0.0

    wd = m.get_u(rh) * 100

    if wd > 45 and wd < 110:
        d1 = wd * 0.01
        dw = math.exp(-30.91 + 4.2967 * d1 - 0.22017 * d1 * d1)
        rh1 = rh + 0.005
        rh2 = rh - 0.005
        wp1 = thermo_dynamics.get_wp(rh1, t)
        wp2 = thermo_dynamics.get_wp(rh2, t)
        wd1 = m.get_u(rh1) * 100
        wd2 = m.get_u(rh2) * 100
        return 998. * dw * abs((wd1 - wd2) * 0.01 / (wp1 - wp2))
    else:
        return 0.0


@pytest.mark.parametrize('name', _materials.get_material_name())
def test_lambda_dsh_mu_l(name):
    """液相水分伝導率が、Fortran の DIFF を書き写した計算と一致することを確認する。

    構造用合板1 は含水率が 0.45 を超える RH 約 98% より上で 0 より大きく、それより下で 0。ほかの材料は常に 0。
    """

    m = _materials.get_material(name)

    t = 293.15

    for rh in [50.0, 90.0, 95.0, 97.0, 98.0, 99.0, 99.5]:

        expected = _fortran_diff(m, rh=rh, t=t)

        assert m.get_lambda_dsh_mu_l(rh=rh, t=t) == pytest.approx(expected, rel=1e-12), f'RH={rh}%'

        if name == '構造用合板1' and rh >= 98.0:
            assert expected > 0.0, f'RH={rh}%'
        else:
            assert expected == 0.0, f'RH={rh}%'
