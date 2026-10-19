import os

import openpyxl
import pandas as pd
import pytest


from modules.materials import Materials
from modules.material_props import FormulaIsotherm, ConstantVaporConductivity, PowerExpVaporConductivity, NoLiquidDiffusivity


# materials_whamcavity.xlsx の内容
_df = pd.read_excel(
    os.path.join(os.path.dirname(__file__), '..', 'modules', 'materials_whamcavity.xlsx'),
    sheet_name='material_prop',
    index_col='name'
)

# 式が1本だけの材料の名前
_single_formula_names = _df.index[_df['n_formula_branches'] == 1].tolist()

# 式を切り替える材料の名前
_multi_formula_names = _df.index[_df['n_formula_branches'] > 1].tolist()

# 湿気伝導率が一定の材料の名前（構造用合板1 は今の実装で湿度依存の式を使っている）
_constant_vapor_names = [name for name in _df.index if name != '構造用合板1']

# 確認する相対湿度, %
# 0% は、軽量モルタルの式（r**-0.120）が今の実装でも計算できないため含めない。
_rhs = list(range(1, 100))

# 境目の前後で追加で確認する相対湿度, %
_rhs_boundary = [88.9, 89.0, 89.1, 89.5, 94.9, 95.0, 95.1, 95.5]


def _make_isotherm(row: pd.Series) -> FormulaIsotherm:
    """Excel の1行から FormulaIsotherm を作る。今の Material.load と同じ順で判定するように並べる。"""

    n = row['n_formula_branches']

    if n == 1:
        candidates = []
    elif n == 2:
        candidates = [(row['threshold2'], row['formula2'])]
    elif n == 3:
        candidates = [(row['threshold3'], row['formula3']), (row['threshold2'], row['formula2'])]
    else:
        raise ValueError(f'n_formula_branches が不正です: {n}')

    # 境目が空欄の組は選ばれることがないので除く
    conditional = tuple((float(t), str(f)) for t, f in candidates if not pd.isna(t))

    return FormulaIsotherm(formula=str(row['formula1']), conditional=conditional)


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


@pytest.mark.parametrize('name', _multi_formula_names)
def test_formula_isotherm_multi(materials, name):
    """式を切り替える材料で、今の Material.get_u と同じ含水率になることを確認する。"""

    current = materials.get_material(name)
    isotherm = _make_isotherm(_df.loc[name])

    for rh in _rhs + _rhs_boundary:
        assert isotherm.u(rh * 0.01) == current.get_u(rh), f'RH={rh}%'


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


@pytest.mark.parametrize('name', _constant_vapor_names)
def test_constant_vapor_conductivity(materials, name):
    """湿気伝導率が一定の材料で、今の Material.get_lambda_dsh_m と同じ値になることを確認する。"""

    current = materials.get_material(name)
    conductivity = ConstantVaporConductivity(value=_df.loc[name, 'moisture_conductivity(kg/msPa)'])

    for rh in _rhs:
        assert conductivity.lambda_dsh_m(rh * 0.01) == current.get_lambda_dsh_m(rh), f'RH={rh}%'


def test_power_exp_vapor_conductivity(materials):
    """構造用合板1 で、今の Material.get_lambda_dsh_m と同じ値になることを確認する。"""

    current = materials.get_material('構造用合板1')

    # 今の Material.get_lambda_dsh_m に直書きされている係数（ASHRAE）
    conductivity = PowerExpVaporConductivity(a=1.87E-11, b=2.4019, c=-0.78864, d=1.1471)

    for rh in _rhs:
        assert conductivity.lambda_dsh_m(rh * 0.01) == current.get_lambda_dsh_m(rh), f'RH={rh}%'


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
