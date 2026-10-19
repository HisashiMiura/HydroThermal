"""材料物性の Excel を読み込み、Material を作る。

Excel の形式ごとの違い（列名、式の与え方、足りない値の補い）は、すべてこのファイルの中で扱う。
Material は、データの与え方を知らない形にしておく。
"""

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

    # 湿気伝導率の部品
    # 構造用合板1 は、湿度によって変わる式（ASHRAE）を使う。
    # 旧 Excel に係数の列がないため、Fortran（Whamcavity.f95）に直書きされている係数を使う。
    # （Fortran の元のコードには「*3.45」がコメントアウトされて残っている。理由は不明。）
    if name == '構造用合板1':
        vapor_conductivity = PowerExpVaporConductivity(a=1.87E-11, b=2.4019, c=-0.78864, d=1.1471)
    else:
        vapor_conductivity = ConstantVaporConductivity(value=moisture_conductivity)

    # 液水拡散係数の部品
    # 構造用合板1 だけ液水が移動する。旧 Excel に係数の列がないため、
    # Fortran（Whamcavity.f95 の DIFF）に直書きされている係数と範囲（含水率 45% を超え 110% 未満）を使う。
    # 部品の範囲は「下限を超え、上限以下」なので、含水率がちょうど 1.10 のときだけ Fortran と異なる。
    # （Fortran では RH 90% を超えるときだけ DIFF を呼んでいたが、構造用合板1 の含水率が 0.45 を超えるのは
    #   RH 約 98% より上なので、範囲の判定だけで同じ結果になる。）
    if name == '構造用合板1':
        liquid_diffusivity = PiecewiseExpPolyDiffusivity(ranges=(
            (0.45, 1.10, (-30.91, 4.2967, -0.22017, 0, 0, 0, 0)),
        ))
    else:
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
