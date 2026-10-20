"""材料物性レビューの共通部品：材料の読み込み、カテゴリの割り当て、指標の計算。

材料の物性値が妥当かを確かめるために、値を「身近な目安」に置き換えた指標を計算する。
図を描く関数は R-2-2 で足す。
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.material_loaders import load_materials  # noqa: E402
from modules.materials import Material  # noqa: E402
from modules.thermo_dynamics import get_dpv_dmu  # noqa: E402


# 材料の出どころ（material_loaders.MATERIAL_SOURCES のキー）
SOURCES = ('whamcavity', 'mews_ashrae')

# 指標を計算する温度, K（20 ℃）
T = 293.15

# 水の密度, kg/m3（容積含水率を求めるのに使う）
RHO_WATER = 1000.0


def delta_air(t: float = T) -> float:
    """静止空気の透湿率（水蒸気圧基準）, (kg/s)/(m Pa)。Schirmer の式（1 気圧）。

    δa = 2.306×10^-5 / (Rv·T) · (T/273.15)^1.81
    （2.306×10^-5 m2/s は 0 ℃・1 気圧の水蒸気の拡散係数、Rv = 461.5 J/(kg K) は水蒸気の気体定数）
    20 ℃ で約 1.94×10^-10。

    Args:
        t: 絶対温度, K
    """
    return 2.306e-5 / (461.5 * t) * (t / 273.15)**1.81


# ---------------------------------------------------------------------------------------------------------------------
# カテゴリ
# ---------------------------------------------------------------------------------------------------------------------

# カテゴリの番号と名前
CATEGORIES = {
    1: '木質ボード',
    2: '製材・木材',
    3: '石膏ボード',
    4: 'セメント・組積',
    5: '繊維系断熱材',
    6: '発泡系断熱材',
    7: '外装・仕上げ',
    8: 'シート・紙類',
    0: 'その他',
}

# 材料のカテゴリ。{カテゴリの番号: [(出どころ, 材料名), ...]}
# どのカテゴリにも入れない材料は「その他」（0）に入れる。
_CATEGORY_MEMBERS = {
    1: [
        ('whamcavity', '構造用合板1'), ('whamcavity', '構造用合板2'), ('whamcavity', '軟質繊維版'),
        ('mews_ashrae', 'MEWS Oriented Strand Board'), ('mews_ashrae', 'MEWS Plywood'),
        ('mews_ashrae', 'MEWS Fibreboard I - Paper Facer'), ('mews_ashrae', 'MEWS Fibreboard II - Plain'),
        ('mews_ashrae', 'MEWS Fibreboard III - Foil Facer'), ('mews_ashrae', 'MEWS Fibreboard IV - Plain'),
        ('mews_ashrae', 'MEWS Fibreboard V - Black Coat'), ('mews_ashrae', 'MEWS Fibreboard VI - Black Coat'),
        ('mews_ashrae', 'MEWS Fibreboard VII - Black Coat'), ('mews_ashrae', 'MEWS Fibreboard VIII - Black Coat'),
        ('mews_ashrae', 'ASHRAE OSB -1'), ('mews_ashrae', 'ASHRAE OSB -2'), ('mews_ashrae', 'ASHRAE OSB -3'),
        ('mews_ashrae', 'ASHRAE Plywood -1'), ('mews_ashrae', 'ASHRAE Plywood -2'), ('mews_ashrae', 'ASHRAE Plywood -3'),
        ('mews_ashrae', 'ASHRAE Fibreboard'),
    ],
    2: [
        ('whamcavity', '木材'), ('whamcavity', '集成材'),
        ('mews_ashrae', 'ASHRAE Eastern White Cedar'), ('mews_ashrae', 'ASHRAE Western Red Cedar'),
        ('mews_ashrae', 'ASHRAE Spruce'), ('mews_ashrae', 'ASHRAE Eastern White Pine'),
        ('mews_ashrae', 'ASHRAE Southern Yellow Pine'),
    ],
    3: [
        ('whamcavity', '石膏ボード'),
        ('mews_ashrae', 'MEWS Exterior Grade Gypsum Board'), ('mews_ashrae', 'ASHRAE Gypsum'),
        ('mews_ashrae', 'ASHRAE Gypsum + Primer'), ('mews_ashrae', 'ASHRAE Gypsum + Primer + Latex'),
    ],
    4: [
        ('whamcavity', 'ALC'), ('whamcavity', '土壁'), ('whamcavity', '軽量モルタル'),
        ('mews_ashrae', 'MEWS Aerated Concrete'),
        ('mews_ashrae', 'MEWS Brick I - White Concrete Brick'), ('mews_ashrae', 'MEWS Brick II - Red Matt Clay Brick'),
        ('mews_ashrae', 'MEWS Brick III - Buff Matt Clay Brick'),
        ('mews_ashrae', 'MEWS Brick IV - Textured Coated Clay Brick'),
        ('mews_ashrae', 'MEWS Brick V - Concrete Brick'), ('mews_ashrae', 'MEWS Brick VI - Calcium Silicate Brick'),
        ('mews_ashrae', 'MEWS Mortar 1-S'), ('mews_ashrae', 'MEWS Mortar 1-N'),
        ('mews_ashrae', 'MEWS Mortar 2-S'), ('mews_ashrae', 'MEWS Mortar 2-N'),
        ('mews_ashrae', 'MEWS Regular Lime Stucco'), ('mews_ashrae', 'MEWS Regular Portland Stucco'),
        ('mews_ashrae', 'MEWS Acrylic Stucco'),
        ('mews_ashrae', 'ASHRAE Clay Brick'), ('mews_ashrae', 'ASHRAE Mortar'), ('mews_ashrae', 'ASHRAE Stucco'),
        ('mews_ashrae', 'ASHRAE Fibre Cement Board'), ('mews_ashrae', 'ASHRAE Cement Board'),
        ('mews_ashrae', 'ASHRAE Lime Stone'),
    ],
    5: [
        ('whamcavity', 'グラスウール1'), ('whamcavity', 'グラスウール2'), ('whamcavity', 'セルロースファイバー'),
        ('mews_ashrae', 'ASHRAE Low-density Glassfibre Batt Insulation'),
        ('mews_ashrae', 'ASHRAE Low-density Glassfibre Batt Insulation (32 kg/m3)'),
        ('mews_ashrae', 'ASHRAE Cellulose Insulation'),
    ],
    6: [
        ('whamcavity', '発泡プラスチック1'), ('whamcavity', '発泡プラスチック2'), ('whamcavity', '発泡プラスチック3'),
        ('mews_ashrae', 'MEWS Spray Polyurethane Foam'),
        ('mews_ashrae', 'ASHRAE Expanded Polystyrene Insulation'),
        ('mews_ashrae', 'ASHRAE Extruded Polystyrene Insulation'),
        ('mews_ashrae', 'ASHRAE Spray Polyurethane Foam Insulation'),
        ('mews_ashrae', 'ASHRAE Polyisocyanurate Insulation'),
        ('mews_ashrae', 'ASHRAE Low-density Polyurethane Foam Insulation'),
    ],
    7: [
        ('whamcavity', 'サイディング'),
        ('mews_ashrae', 'MEWS Siding I - OSB'), ('mews_ashrae', 'MEWS Siding II - Plywood'),
        ('mews_ashrae', 'MEWS Siding III - Fibreboard'), ('mews_ashrae', 'MEWS Siding IV - Fibreboard'),
        ('mews_ashrae', 'MEWS Siding V - Fibreboard'), ('mews_ashrae', 'MEWS EIFS Base Coat + Finish Coat'),
        ('mews_ashrae', 'ASHRAE Composite Wood Siding'), ('mews_ashrae', 'ASHRAE EIFS Base Coat and Finish Coat'),
        ('mews_ashrae', 'ASHRAE Vinyl Wallpaper'),
    ],
    8: [
        ('mews_ashrae', 'MEWS Building Membrane IA'), ('mews_ashrae', 'MEWS Building Membrane II'),
        ('mews_ashrae', 'MEWS Building Membrane III'), ('mews_ashrae', 'MEWS Building Membrane IVA'),
        ('mews_ashrae', 'MEWS Building Membrane V A'), ('mews_ashrae', 'MEWS Building Membrane V C'),
        ('mews_ashrae', 'MEWS Building Membrane VI'), ('mews_ashrae', 'MEWS Building Membrane VII'),
        ('mews_ashrae', 'MEWS Building Membrane VIII'), ('mews_ashrae', 'MEWS Building Membrane IX'),
        ('mews_ashrae', 'ASHRAE #15 Felt'), ('mews_ashrae', 'ASHRAE 10 min Paper'),
        ('mews_ashrae', 'ASHRAE 30 min Paper'), ('mews_ashrae', 'ASHRAE 60 min Paper'),
        ('mews_ashrae', 'ASHRAE Spun Bonded Polyolefin Membrane'),
        ('mews_ashrae', 'ASHRAE Bonded Polyolefin Membrane (Crinkled )'),
    ],
    # どのカテゴリにも入れない材料（シージングとサーモプライは中身が分からない、通気層と Air は空気。2026-10-21 にユーザーと確認）
    0: [
        ('whamcavity', 'シージング'), ('whamcavity', '通気層'), ('whamcavity', 'サーモプライ'),
        ('mews_ashrae', 'Air'),
    ],
}

# {(出どころ, 材料名): カテゴリの番号}
MATERIAL_CATEGORY = {key: category for category, keys in _CATEGORY_MEMBERS.items() for key in keys}


def load_all() -> list[tuple[str, Material]]:
    """両方の出どころの全材料を、(出どころ, Material) の組で読み込む（出どころの順、Excel の順）。"""
    return [(source, m) for source in SOURCES for m in load_materials(source)]


def get_category(source: str, name: str) -> int:
    """材料のカテゴリの番号を返す。割り当ての表にない材料はエラーにする（割り当て忘れを防ぐため）。"""
    if (source, name) not in MATERIAL_CATEGORY:
        raise KeyError(f'カテゴリが割り当てられていない材料です: {source}, {name}')
    return MATERIAL_CATEGORY[(source, name)]


# ---------------------------------------------------------------------------------------------------------------------
# 指標
# ---------------------------------------------------------------------------------------------------------------------

# 指標の列名と説明（indicators.csv の列の順）
INDICATOR_COLUMNS = {
    'source': '材料の出どころ',
    'name': '材料名',
    'category': 'カテゴリの番号',
    'category_name': 'カテゴリ',
    'rho': '乾燥密度, kg/m3',
    'c': '比熱, J/(kg K)',
    'lambda_h': '熱伝導率, W/(m K)',
    'c_rho': '容積比熱, kJ/(m3 K)',
    'u50': '平衡含水率 RH 50%, kg/kg',
    'u80': '平衡含水率 RH 80%, kg/kg',
    'u95': '平衡含水率 RH 95%, kg/kg',
    'u100': '平衡含水率 RH 100%, kg/kg',
    'psi100': '容積含水率 RH 100%（u100 × 密度 ÷ 1000）, m3/m3。1 を超えるとありえない',
    'mu50': '透湿抵抗比 μ RH 50%（静止空気の透湿率 ÷ 湿気伝導率）。1 より小さいとありえない',
    'mu90': '透湿抵抗比 μ RH 90%',
    'dw95': '液水拡散係数 RH 95% の含水率で, m2/s',
    'dw99': '液水拡散係数 RH 99% の含水率で, m2/s',
    'rh_liquid': '液水伝導率が湿気伝導率（化学ポテンシャル基準）を超える最初の RH, %（超えなければ空欄）。'
                 '液水伝導率は今のプログラムどおり水の密度 998 を掛けた値（未決事項 1）',
    'flags': '気になる点（ψ>1、μ<1 など）',
}

# 液水伝導率と湿気伝導率を比べる相対湿度, %
_RHS_LIQUID = [rh / 10 for rh in range(500, 1000)]


def _safe(f, *args) -> float:
    """計算できないとき（0 の負の数乗など）は NaN を返す。"""
    try:
        return float(f(*args))
    except (ZeroDivisionError, ValueError, OverflowError):
        return math.nan


def _mu(m: Material, rh: float) -> float:
    """透湿抵抗比 μ。湿気伝導率が 0 なら NaN（μ は無限大になるが、表では空欄にする）。"""
    lambda_dsh_m = _safe(m.get_lambda_dsh_m, rh)
    return delta_air() / lambda_dsh_m if lambda_dsh_m > 0 else math.nan


def _rh_liquid(m: Material) -> float:
    """液水伝導率が湿気伝導率（化学ポテンシャル基準）を超える最初の相対湿度, %。超えなければ NaN。"""
    for rh in _RHS_LIQUID:
        liquid = _safe(m.get_lambda_dsh_mu_l, rh, T)
        vapour = _safe(m.get_lambda_dsh_m, rh) * get_dpv_dmu(rh=rh, t=T)
        if liquid > vapour:
            return rh
    return math.nan


def indicators(source: str, m: Material) -> dict:
    """1 つの材料の指標を計算する（列は INDICATOR_COLUMNS）。"""

    category = get_category(source, m.name)
    u = {rh: _safe(m.get_u, rh) for rh in (50, 80, 95, 99, 100)}
    psi100 = u[100] * m.rho / RHO_WATER
    mu50 = _mu(m, 50)
    mu90 = _mu(m, 90)

    flags = []
    if psi100 > 1:
        flags.append(f'ψ(100%)={psi100:.4g}>1')
    for rh, mu in ((50, mu50), (90, mu90)):
        if mu < 1:
            flags.append(f'μ({rh}%)={mu:.3g}<1')

    return {
        'source': source,
        'name': m.name,
        'category': category,
        'category_name': CATEGORIES[category],
        'rho': m.rho,
        'c': m.c,
        'lambda_h': m.lambda_h,
        'c_rho': m.c_rho / 1000,
        'u50': u[50],
        'u80': u[80],
        'u95': u[95],
        'u100': u[100],
        'psi100': psi100,
        'mu50': mu50,
        'mu90': mu90,
        'dw95': _safe(m.liquid_diffusivity.d_w, u[95]),
        'dw99': _safe(m.liquid_diffusivity.d_w, u[99]),
        'rh_liquid': _rh_liquid(m),
        'flags': '; '.join(flags),
    }
