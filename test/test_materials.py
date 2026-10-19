import pytest


from modules.materials import Materials
from modules.material_props import FormulaIsotherm


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

