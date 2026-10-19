import os

import pandas as pd
import pytest


from modules.materials import Materials
from modules.material_props import FormulaIsotherm


# materials_whamcavity.xlsx の内容
_df = pd.read_excel(
    os.path.join(os.path.dirname(__file__), '..', 'modules', 'materials_whamcavity.xlsx'),
    sheet_name='material_prop',
    index_col='name'
)

# 式が1本だけの材料の名前
_single_formula_names = _df.index[_df['n_formula_branches'] == 1].tolist()

# 確認する相対湿度, %
# 0% は、軽量モルタルの式（r**-0.120）が今の実装でも計算できないため含めない。
_rhs = list(range(1, 100))


@pytest.fixture(scope='module')
def materials():
    return Materials()


@pytest.mark.parametrize('name', _single_formula_names)
def test_formula_isotherm_single(materials, name):
    """式1本の材料で、今の Material.get_u と同じ含水率になることを確認する。"""

    current = materials.get_material(name)
    isotherm = FormulaIsotherm(formula=str(_df.loc[name, 'formula1']))

    for rh in _rhs:
        assert isotherm.u(rh * 0.01) == current.get_u(rh), f'RH={rh}%'
