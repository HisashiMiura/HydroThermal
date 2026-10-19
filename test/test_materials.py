import math

import pytest


from modules import thermo_dynamics
from modules.materials import Materials
from modules.material_props import (
    FormulaIsotherm,
    ConstantVaporConductivity,
    PowerExpVaporConductivity,
    NoLiquidDiffusivity,
    PiecewiseExpPolyDiffusivity,
)


_materials = Materials()

# 確認する相対湿度, %
# 0% は、軽量モルタルの式（r**-0.120）が今の実装でも計算できないため含めない。
_rhs = list(range(1, 100))


def test_load():

    ms = Materials()

    m = ms.get_material('シージング')

    assert m.lambda_h == 0.0586
    assert m.lambda_dsh_m == 2.61E-11
    assert m.c == 0.0
    assert m.rho == 0.0


@pytest.mark.parametrize('name', _materials.get_material_name())
def test_isotherm(name):
    """平衡含水率の部品が入っていて、今の get_u と同じ含水率になることを確認する。"""

    m = _materials.get_material(name)

    assert isinstance(m.isotherm, FormulaIsotherm)

    for rh in _rhs:
        assert m.isotherm.u(rh * 0.01) == m.get_u(rh), f'RH={rh}%'


@pytest.mark.parametrize('name', _materials.get_material_name())
def test_vapor_conductivity(name):
    """湿気伝導率の部品が入っていて、今の get_lambda_dsh_m と同じ値になることを確認する。"""

    m = _materials.get_material(name)

    if name == '構造用合板1':
        assert isinstance(m.vapor_conductivity, PowerExpVaporConductivity)
    else:
        assert isinstance(m.vapor_conductivity, ConstantVaporConductivity)

    for rh in _rhs:
        assert m.vapor_conductivity.lambda_dsh_m(rh * 0.01) == m.get_lambda_dsh_m(rh), f'RH={rh}%'


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
