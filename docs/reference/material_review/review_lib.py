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


# ---------------------------------------------------------------------------------------------------------------------
# 図
# ---------------------------------------------------------------------------------------------------------------------

import csv  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# 図の保存先
FIGURES = os.path.join(HERE, 'figures')

# 文献の数値を書き写した CSV の置き場所
REF_DATA = os.path.join(HERE, 'ref_data')

# 系列の色（決まった順に使う。色覚の多様性を考えて検証済みの 8 色。9 色目は作らない）
SERIES_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']

# 線の種類（同じ値で線が重なる材料も見分けられるように、色と一緒に変える）
LINESTYLES = ['-', '--', ':', '-.']

# 文献の値の点の印（色は黒・灰色で、Excel の材料の線と区別する）
REF_MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', '*']

# 文字・軸・格子の色
INK = '#0b0b0b'
INK_SECONDARY = '#52514e'
GRID = '#d9d8d4'

plt.rcParams.update({
    'font.family': 'Hiragino Sans',
    'font.size': 9,
    'axes.edgecolor': INK_SECONDARY,
    'axes.labelcolor': INK,
    'xtick.color': INK_SECONDARY,
    'ytick.color': INK_SECONDARY,
    'axes.grid': True,
    'grid.color': GRID,
    'grid.linewidth': 0.6,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'legend.frameon': False,
})

# 曲線を描く相対湿度, %（高湿域を細かく）
RHS_CURVE = np.concatenate([np.arange(1.0, 95.0, 0.5), np.arange(95.0, 100.0001, 0.05)])


def read_refs(file_name: str) -> list[dict]:
    """文献の数値の CSV（ref_data/ の中）を読む。

    列: doc（文献の略称）, page（PDF のページ）, table（表・図の番号）, material（文献の材料名・試料）,
        property（u, lambda_dsh_m, dw, lambda_h, rho, mu）, x（相対湿度 % または含水率 kg/kg。property によっては空欄）,
        value（値）, note（吸湿・放湿の別、密度など）
    """
    with open(os.path.join(REF_DATA, file_name), encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r['x'] = float(r['x']) if r['x'] else math.nan
        r['value'] = float(r['value'])
    return rows


def _ref_series(refs: list[dict], prop: str) -> dict:
    """文献の値を、(文献, 表, 材料, 注記) ごとの点の並びにまとめる。{ラベル: (xs, ys)}"""
    series = {}
    for r in refs:
        if r['property'] != prop:
            continue
        label = f"{r['doc']} p{r['page']} {r['material']}" + (f"（{r['note']}）" if r['note'] else '')
        xs, ys = series.setdefault(label, ([], []))
        xs.append(r['x'])
        ys.append(r['value'])
    return series


def _check_series(materials: list) -> None:
    if len(materials) > len(SERIES_COLORS):
        raise ValueError(f'1 枚の図に描ける材料は {len(SERIES_COLORS)} つまでです（{len(materials)} 個）。図を分けてください。')


def _positive(values) -> np.ndarray:
    """対数目盛りに描くため、0 以下の値を NaN（描かない）にする。"""
    values = np.array(values, dtype=float)
    return np.where(values > 0, values, np.nan)


def plot_moisture(materials: list[tuple[str, str]], refs: list[dict] = (), title: str = '',
                  file_name: str | None = None, rh_min: float = 0.0):
    """水分物性の曲線（4 枚組）を描く。Excel の材料は色つきの線、文献の値は黒・灰色の点。

    1. 平衡含水率 u と相対湿度
    2. 湿気伝導率（対数）と相対湿度。左端に静止空気の透湿率（μ = 1）の線を引く
    3. 液水伝導率（対数）と相対湿度（20 ℃。水の密度 998 を掛けた今のプログラムの値）
    4. 液水拡散係数（対数）と含水率（0 から RH 100% の含水率まで）

    Args:
        materials: (出どころ, 材料名) の一覧（8 つまで）
        refs: 文献の値（read_refs の行）。property が u・lambda_dsh_m・dw の行を点で描く
        title: 図の題
        file_name: 保存するファイル名（figures/ の中）。省略すると保存しない
        rh_min: 相対湿度の軸の左端, %
    """

    _check_series(materials)
    ms = {(source, m.name): m for source, m in load_all()}

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.2), layout='constrained')
    ax_u, ax_vap, ax_liq, ax_dw = axes.flat
    rhs = RHS_CURVE[RHS_CURVE >= rh_min]

    for k, key in enumerate(materials):
        m = ms[key]
        style = dict(color=SERIES_COLORS[k], linestyle=LINESTYLES[k % len(LINESTYLES)], linewidth=2,
                     label=f'{key[1]}（{key[0]}）')
        ax_u.plot(rhs, [_safe(m.get_u, rh) for rh in rhs], **style)
        ax_vap.plot(rhs, _positive([_safe(m.get_lambda_dsh_m, rh) for rh in rhs]), **style)
        ax_liq.plot(rhs, _positive([_safe(m.get_lambda_dsh_mu_l, rh, T) for rh in rhs]), **style)
        us = np.linspace(_safe(m.get_u, rhs[0]), _safe(m.get_u, 100.0), 400)
        ax_dw.plot(us, _positive([_safe(m.liquid_diffusivity.d_w, u) for u in us]), **style)

    for ax, prop in ((ax_u, 'u'), (ax_vap, 'lambda_dsh_m'), (ax_dw, 'dw')):
        for j, (label, (xs, ys)) in enumerate(_ref_series(refs, prop).items()):
            ax.plot(xs, ys, linestyle='none', marker=REF_MARKERS[j % len(REF_MARKERS)], markersize=6,
                    markerfacecolor='white', markeredgecolor=INK if j < len(REF_MARKERS) else INK_SECONDARY,
                    markeredgewidth=1.2, label=label)

    ax_vap.axhline(delta_air(), color=INK_SECONDARY, linewidth=1, linestyle=(0, (4, 3)))
    ax_vap.annotate('静止空気（μ = 1）', xy=(rhs[0], delta_air()), xytext=(2, 3), textcoords='offset points',
                    color=INK_SECONDARY, fontsize=8)

    ax_u.set(xlabel='相対湿度, %', ylabel='平衡含水率, kg/kg', title='平衡含水率', xlim=(rh_min, 100))
    ax_vap.set(xlabel='相対湿度, %', ylabel='湿気伝導率, (kg/s)/(m Pa)', title='湿気伝導率', xlim=(rh_min, 100),
               yscale='log')
    ax_liq.set(xlabel='相対湿度, %', ylabel='液水伝導率, (kg/s)/(m (J/kg))', title='液水伝導率（20 ℃）',
               xlim=(rh_min, 100), yscale='log')
    ax_dw.set(xlabel='含水率, kg/kg', ylabel='液水拡散係数, m2/s', title='液水拡散係数', yscale='log')
    for ax in axes.flat:
        ax.grid(True, which='major')

    handles, labels = [], []
    for ax in (ax_u, ax_vap, ax_dw):
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in labels:
                handles.append(h)
                labels.append(lab)
    fig.legend(handles, labels, loc='outside lower center', ncol=2, fontsize=8)
    if title:
        fig.suptitle(title)

    return _finish(fig, file_name)


def plot_mu(materials: list[tuple[str, str]], ref_ranges: dict | None = None, title: str = '',
            file_name: str | None = None):
    """透湿抵抗比 μ を、材料ごとに RH 50% と RH 90% の 2 点で描く（対数目盛り）。

    Args:
        materials: (出どころ, 材料名) の一覧（何個でもよい。上から順に並べる）
        ref_ranges: 文献の μ の範囲 {(出どころ, 材料名): (下限, 上限, 文献の略称)}。灰色の帯で描く
        title: 図の題
        file_name: 保存するファイル名（figures/ の中）
    """

    ms = {(source, m.name): m for source, m in load_all()}
    ref_ranges = ref_ranges or {}
    ys = np.arange(len(materials))

    fig, ax = plt.subplots(figsize=(8, 0.32 * len(materials) + 1.4), layout='constrained')

    for y, key in zip(ys, materials):
        if key in ref_ranges:
            lo, hi, _ = ref_ranges[key]
            ax.plot([lo, hi], [y, y], color=GRID, linewidth=9, solid_capstyle='round', zorder=1)
        mu50, mu90 = _mu(ms[key], 50), _mu(ms[key], 90)
        if math.isnan(mu50) and math.isnan(mu90):
            # 湿気伝導率が 0（μ は無限大）の材料は、点の代わりに文字で示す
            ax.annotate('湿気伝導率 0（μ = ∞）', xy=(1, y), xytext=(6, 0), textcoords='offset points',
                        color=INK_SECONDARY, fontsize=8, va='center')
        ax.plot([mu50, mu90], [y, y], color=INK_SECONDARY, linewidth=1, zorder=2)
    mu50s = [_mu(ms[key], 50) for key in materials]
    mu90s = [_mu(ms[key], 90) for key in materials]
    ax.plot(mu50s, ys, linestyle='none', marker='o', markersize=8, color=SERIES_COLORS[0], label='RH 50%', zorder=3)
    ax.plot(mu90s, ys, linestyle='none', marker='o', markersize=8, color=SERIES_COLORS[1], label='RH 90%', zorder=3)
    if ref_ranges:
        ax.plot([], [], color=GRID, linewidth=9, label='文献の範囲')

    ax.axvline(1, color=INK_SECONDARY, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate('μ = 1（静止空気）', xy=(1, -0.5), xytext=(3, 0), textcoords='offset points', color=INK_SECONDARY,
                fontsize=8, va='bottom')
    ax.set_yticks(ys, [f'{name}（{source}）' for source, name in materials], fontsize=8)
    ax.set_ylim(len(materials) - 0.5, -0.8)
    ax.set_xscale('log')
    ax.set_xlabel('透湿抵抗比 μ（静止空気の透湿率 ÷ 材料の湿気伝導率）')
    ax.grid(True, axis='x', which='major')
    ax.grid(False, axis='y')
    fig.legend(loc='outside lower center', ncol=3, fontsize=8)
    if title:
        fig.suptitle(title)

    return _finish(fig, file_name)


# 熱伝導率と密度の散布図で、カテゴリに使う色（カテゴリの番号の順。その他は灰色）
CATEGORY_COLORS = {category: SERIES_COLORS[category - 1] for category in range(1, 9)} | {0: '#a3a29b'}


def plot_lambda_rho(refs: list[dict] = (), highlight: int | None = None, title: str = '熱伝導率と密度',
                    file_name: str | None = None):
    """全材料の熱伝導率と密度の散布図（両対数）。カテゴリで色分けし、文献の値を黒い印で重ねる。

    Args:
        refs: 文献の値（property が lambda_h で、x に密度を入れた行）
        highlight: 強調するカテゴリの番号（ほかのカテゴリは薄くする）。省略するとすべて同じ濃さ
        title: 図の題
        file_name: 保存するファイル名（figures/ の中）
    """

    fig, ax = plt.subplots(figsize=(8, 6), layout='constrained')

    points = {}
    for source, m in load_all():
        if m.rho <= 0 or m.lambda_h <= 0:
            continue
        points.setdefault(get_category(source, m.name), []).append((m.rho, m.lambda_h))

    for category, name in CATEGORIES.items():
        if category not in points:
            continue
        xs, ys = zip(*points[category])
        alpha = 1.0 if highlight in (None, category) else 0.2
        ax.plot(xs, ys, linestyle='none', marker='o', markersize=7, color=CATEGORY_COLORS[category],
                markeredgecolor='white', markeredgewidth=1, alpha=alpha, label=f'{category} {name}' if category else name)

    for j, (label, (xs, ys)) in enumerate(_ref_series(refs, 'lambda_h').items()):
        ax.plot(xs, ys, linestyle='none', marker=REF_MARKERS[j % len(REF_MARKERS)], markersize=7,
                markerfacecolor='white', markeredgecolor=INK, markeredgewidth=1.2, label=label)

    ax.set(xscale='log', yscale='log', xlabel='乾燥密度, kg/m3', ylabel='熱伝導率, W/(m K)', title=title)
    ax.grid(True, which='major')
    legend = fig.legend(loc='outside right upper', fontsize=8)
    for handle in legend.legend_handles:
        handle.set_alpha(1.0)  # 薄くしたカテゴリも、凡例では見えるようにする

    return _finish(fig, file_name)


def _finish(fig, file_name: str | None):
    """図を保存する（file_name があれば）。図を返す。"""
    if file_name:
        os.makedirs(FIGURES, exist_ok=True)
        fig.savefig(os.path.join(FIGURES, file_name), dpi=130)
    return fig
