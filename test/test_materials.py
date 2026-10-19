import pytest


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
    assert m.psi0 == 0.0


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
    （今の DIFF は呼ばれるとエラーで止まるため、値は比べない。）
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
