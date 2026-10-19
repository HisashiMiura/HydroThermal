"""材料物性の Excel を読み込み、Material を作る。

Excel の形式ごとの違い（列名、式の与え方、足りない値の補い）は、すべてこのファイルの中で扱う。
Material は、データの与え方を知らない形にしておく。
"""

import logging
import math
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


def _liquid_diffusivity_from_ranges(
        n_ranges: int,
        ranges: list[tuple[float, float, tuple[float, float, float, float, float, float, float]]],
        name: str = '',
        u_saturation: float | None = None
) -> NoLiquidDiffusivity | PiecewiseExpPolyDiffusivity:
    """新しい Excel（materials_mews_ashrae.xlsx）の「範囲分け数」と区間の値から、液水拡散係数の部品を作る。

    各区間の式は次のとおり（定義は RR-110 の式(5)、Jl = −ρ0·Dw·grad u）。
        D = exp(a + b·u + c·u^2 + d·u^3 + e·u^4 + f·u^5 + g·u^6)    u: 質量含水率, kg/kg、D: m2/s

    範囲分け数ごとの扱い:
        0: 液水が移動しない（係数の値は使わない。a に「測っていない」の印 ln(99999) が入っている材料もある）
        1: 区間1の式を、含水率によらず使う（Excel の範囲は使わない）
        2・3: 区間1から範囲分け数の区間までを使う。区間1の下限は Excel に値がないので −∞ とする。
              最後の区間の上限を超える含水率には、上限での値で一定の区間を足す（下の説明）
        4: 3 として読む（下の説明）
        それ以外: Excel の誤りとして ValueError にする

    区間と区間のすき間の埋め方（2026-10-20 に決定）:
        Excel では、前の区間の上限と次の区間の下限が違う（すき間がある）材料がある。
        （No.49・62・66・67・68・76・77・78・80 の 9 材料。すべて ASHRAE で、区間1 は 10^-16（実質 0）の定数）
        すき間の含水率ではどの区間の式も当てはまらないので、前の区間の上限を次の区間の下限まで延ばして埋める。
        例: No.76 Gypsum は 区間1「〜0.13」・区間2「0.15〜0.57」→ 区間1を「〜0.15」とする。
        理由:
            - ASHRAE の材料は、測った範囲（区間2）より下をすべて 10^-16 としている。すき間も測った範囲より下なので同じ扱いにする。
            - 次の区間を下に延ばすと、測った範囲の外で多項式を使い、測っていない液水移動を作ってしまう。
        埋めたときは、材料名と値をログ（INFO）に出す。Excel の値は変えない。
        区間が重なっている（前の区間の上限が次の区間の下限より大きい）ときは、Excel の誤りとして ValueError にする。

    最後の区間の上限を超える含水率の扱い（2026-10-20 に決定）:
        Excel の区間は最後の区間の上限で終わっていて、それを超える含水率にはどの区間の式も当てはまらない。
        最後の区間の後ろに「上限から +∞ まで、上限での値で一定」の区間を足す（多項式の材料は上限での値を計算して定数にする）。
        例: No.49 Fibreboard は最後の区間「0.094〜1.5」（6次式）→ 含水率 1.5 を超えたら 1.5 での値 1.0×10^-9 m2/s で一定。
        理由:
            - MEWS も ASHRAE も、測った範囲より上は「端の値で一定」として延ばしている。その延ばし方を上限の外まで続ける。
            - 0 にすると、RH 100% 近くで拡散係数が急に 0 になる（9 材料: No.27・28・49・58・63・66・67・73・74）。
            - 最後の区間の式をそのまま延ばすと、範囲の外で多項式を使うことになり、No.49 では 10^-81 まで下がる。
        RH 100% の平衡含水率 u_saturation が最後の区間の上限より大きい（計算結果が変わる）材料だけ、材料名と値をログ（INFO）に出す。
        ほかの材料は含水率が上限を超えないので、足した区間は使われない。Excel の値は変えない。

    範囲分け数 4 の扱い（2026-10-20 に決定）:
        No.27 MEWS Fibreboard I - Paper Facer だけが範囲分け数 4 だが、Excel には区間3までの欄しかなく、値も3区間分しかない。
        ほかの Fibreboard は「下側の定数 ＋ 測った範囲の多項式 ＋ 上側の定数」の3区間で、No.27 は測った範囲を2本の多項式
        （区間2・3）に分けたため、上側の定数の区間4 が入りきらなかったと見られる（推測）。
        範囲分け数 3 として読み、区間3の上限 0.53 を超える含水率は、上の決まりで上限での値（3.7×10^-10 m2/s）で一定とする。
        これは欠けている区間4 を「端の値で一定」で補うことになり、MEWS の作り方に合う。読み替えたときはログ（WARNING）に出す。

    Args:
        n_ranges: 範囲分け数
        ranges: 区間1から順に (下限, 上限, 係数 (a, b, c, d, e, f, g)) を並べたもの。下限・上限は質量含水率, kg/kg
        name: 材料の名前（ログとエラーのメッセージに使う）
        u_saturation: RH 100% の平衡含水率, kg/kg（ログを出すかどうかの判断だけに使う。省略するとログを出さない）
    Returns:
        液水拡散係数の部品
    """

    if n_ranges == 4:
        logger.warning('%s: 液水拡散係数の範囲分け数 4 を 3 として読みました（Excel には区間3までの値しかないため）', name)
        n_ranges = 3

    if n_ranges == 0:
        return NoLiquidDiffusivity()

    if n_ranges == 1:
        _, _, coefficients = ranges[0]
        return PiecewiseExpPolyDiffusivity(ranges=((-math.inf, math.inf, tuple(coefficients)),))

    if n_ranges in (2, 3):
        _, upper1, coefficients1 = ranges[0]
        used = [(-math.inf, upper1, tuple(coefficients1))]
        used += [(lower, upper, tuple(coefficients)) for lower, upper, coefficients in ranges[1:n_ranges]]

        # 区間と区間のすき間を、前の区間の上限を次の区間の下限まで延ばして埋める
        for i in range(n_ranges - 1):
            lower, upper, coefficients = used[i]
            next_lower = used[i + 1][0]
            if upper > next_lower:
                raise ValueError(f'{name}: 液水拡散係数の区間{i + 1}（上限 {upper}）と区間{i + 2}（下限 {next_lower}）が重なっています')
            if upper < next_lower:
                logger.info('%s: 液水拡散係数の区間%dと区間%dのすき間（%s〜%s）を、区間%dを延ばして埋めました',
                            name, i + 1, i + 2, upper, next_lower, i + 1)
                used[i] = (lower, next_lower, coefficients)

        # 最後の区間の上限を超える含水率は、上限での値で一定とする
        _, upper_last, coefficients_last = used[-1]
        a_last = sum(c * upper_last**k for k, c in enumerate(coefficients_last))
        used.append((upper_last, math.inf, (a_last, 0, 0, 0, 0, 0, 0)))
        if u_saturation is not None and u_saturation > upper_last:
            logger.info('%s: 液水拡散係数の最後の区間の上限 %s を超える含水率（RH 100%% で %.3g）は、上限での値 %.2g m2/s で一定としました',
                        name, upper_last, u_saturation, math.exp(a_last))

        return PiecewiseExpPolyDiffusivity(ranges=tuple(used))

    raise ValueError(f'{name}: 液水拡散係数の範囲分け数が不正です: {n_ranges}')
