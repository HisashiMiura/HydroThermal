"""材料物性の Excel を読み込み、Material を作る。

Excel の形式ごとの違い（列名、式の与え方、足りない値の補い）は、すべてこのファイルの中で扱う。
Material は、データの与え方を知らない形にしておく。
"""

import logging
import os

import pandas as pd
from pandas import Series

from modules.materials import Material
from modules.material_props import (
    FormulaIsotherm,
    ConstantVaporConductivity,
    PowerExpVaporConductivity,
    NoLiquidDiffusivity,
    PiecewiseExpPolyDiffusivity,
)


logger = logging.getLogger(__name__)

# 旧 Excel（Fortran 版の19材料）
WHAMCAVITY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'materials_whamcavity.xlsx')

# 旧 Excel に列がないため、Fortran（Whamcavity.f95）に直書きされている値で補う材料。
# {材料名: (湿気伝導率の部品, 液水拡散係数の部品)}
_WHAMCAVITY_SUPPLEMENTS = {

    '構造用合板1': (

        # 湿気伝導率：湿度によって変わる式（ASHRAE）。
        # （Fortran の元のコードには「*3.45」がコメントアウトされて残っている。理由は不明。）
        PowerExpVaporConductivity(a=1.87E-11, b=2.4019, c=-0.78864, d=1.1471),

        # 液水拡散係数：Fortran の DIFF の係数と範囲（含水率 45% を超え 110% 未満）。
        # 部品の範囲は「下限を超え、上限以下」なので、含水率がちょうど 1.10 のときだけ Fortran と異なる。
        # （Fortran では RH 90% を超えるときだけ DIFF を呼んでいたが、構造用合板1 の含水率が 0.45 を超えるのは
        #   RH 約 98% より上なので、範囲の判定だけで同じ結果になる。）
        PiecewiseExpPolyDiffusivity(ranges=(
            (0.45, 1.10, (-30.91, 4.2967, -0.22017, 0, 0, 0, 0)),
        )),
    ),
}


def load_whamcavity(path: str = WHAMCAVITY_FILE) -> list[Material]:
    """旧 Excel（materials_whamcavity.xlsx）を読み込み、Material の一覧を作る。

    Args:
        path: Excel ファイルのパス（省略すると modules/materials_whamcavity.xlsx）
    Returns:
        Material の一覧
    """

    if not os.path.isfile(path):
        raise FileNotFoundError(f'材料物性ファイルが見つかりません: {path}')

    df = pd.read_excel(path, sheet_name='material_prop', index_col='name')

    # インデックス（name）に重複がないかチェック
    if not df.index.is_unique:
        # 重複している名前を特定してエラーメッセージに入れる
        duplicates = df.index[df.index.duplicated()].unique().tolist()
        raise ValueError(f"{os.path.basename(path)} の 'name' 列に重複があります: {duplicates}")

    # 1行ずつ取り出して Material を作る
    ms = [_material_from_whamcavity_row(name=name, row=row) for name, row in df.iterrows()]

    logger.info('材料物性データの読み込みに成功しました: %s（%d件）', os.path.basename(path), len(ms))

    return ms


def _material_from_whamcavity_row(name: str, row: Series) -> Material:
    """旧 Excel（materials_whamcavity.xlsx）の1行から Material を作る。

    Args:
        name: 材料の名前
        row: Excel の1行
    Returns:
        Material
    """

    # 熱伝導率, W/(m K)
    thermal_conductivity = row['thermal_conductivity(W/mK)']
    # 湿気伝導率, (kg/s)/(m Pa)
    moisture_conductivity = row['moisture_conductivity(kg/msPa)']
    # 比熱, J/(kg K)
    specific_heat = row['specific_heat(J/kgK)']
    # 密度, kg/m3
    density = row['density(kg/m3)']

    n_formula_branches = row['n_formula_branches']
    formula1 = str(row['formula1'])
    formula2 = str(row['formula2'])
    formula3 = str(row['formula3'])
    threshold2 = row['threshold2']
    threshold3 = row['threshold3']

    # 平衡含水率の部品
    # 旧 Excel では境目3 が境目2 より大きい前提なので、境目3 → 境目2 の順に調べるように並べる。
    if n_formula_branches == 1:
        candidates = []
    elif n_formula_branches == 2:
        candidates = [(threshold2, formula2)]
    elif n_formula_branches == 3:
        candidates = [(threshold3, formula3), (threshold2, formula2)]
    else:
        raise ValueError(f'{name}: n_formula_branches が不正です: {n_formula_branches}')

    # 境目が空欄の組は選ばれることがないので除く
    conditional = tuple((float(t), f) for t, f in candidates if not pd.isna(t))

    isotherm = FormulaIsotherm(formula=formula1, conditional=conditional)

    # 湿気伝導率と液水拡散係数の部品
    # 旧 Excel の湿気伝導率は固定値だけで、液水拡散係数の列はない。
    # 補う値がある材料（_WHAMCAVITY_SUPPLEMENTS）はその値を、ほかの材料は固定値と「液水が移動しない」を使う。
    if name in _WHAMCAVITY_SUPPLEMENTS:
        vapor_conductivity, liquid_diffusivity = _WHAMCAVITY_SUPPLEMENTS[name]
    else:
        vapor_conductivity = ConstantVaporConductivity(value=moisture_conductivity)
        liquid_diffusivity = NoLiquidDiffusivity()

    return Material(
        name=name,
        lambda_h=thermal_conductivity,
        lambda_dsh_m=moisture_conductivity,
        c=specific_heat,
        rho=density,
        isotherm=isotherm,
        vapor_conductivity=vapor_conductivity,
        liquid_diffusivity=liquid_diffusivity
    )
