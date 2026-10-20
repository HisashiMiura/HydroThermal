"""① 木質ボードのレビューの図を描き、figures/wood_boards/ に保存する。

材料ごとに 4 枚（平衡含水率、湿気伝導率、液水拡散係数、熱伝導率と密度）と、まとめの図 2 枚（μ、熱伝導率と密度）。
検証する材料は色、同じグループのほかの材料は灰色、文献の値は黒い印で描く。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_wood_boards.py
"""

import logging

import review_lib as R

# 文献の数値（建築学会の本 p51〜59、エース 表 7.2）
REFS = R.read_refs('wood_boards.csv')

W = 'whamcavity'
M = 'mews_ashrae'

# グループ：材料（図のファイル名に使う短い名前と、(出どころ, 材料名)）と、重ねる文献の材料名
GROUPS = {
    'plywood': dict(
        materials={
            'ply_w1': (W, '構造用合板1'), 'ply_w2': (W, '構造用合板2'), 'ply_mews': (M, 'MEWS Plywood'),
            'ply_a1': (M, 'ASHRAE Plywood -1'), 'ply_a2': (M, 'ASHRAE Plywood -2'), 'ply_a3': (M, 'ASHRAE Plywood -3'),
        },
        refs=('合板',),
    ),
    'osb': dict(
        materials={
            'osb_mews': (M, 'MEWS Oriented Strand Board'), 'osb_a1': (M, 'ASHRAE OSB -1'),
            'osb_a2': (M, 'ASHRAE OSB -2'), 'osb_a3': (M, 'ASHRAE OSB -3'),
        },
        refs=('ウエハーボード', 'パーティクルボード'),
    ),
    'fibreboard': dict(
        materials={
            'fb_w': (W, '軟質繊維版'),
            'fb_m1': (M, 'MEWS Fibreboard I - Paper Facer'), 'fb_m2': (M, 'MEWS Fibreboard II - Plain'),
            'fb_m3': (M, 'MEWS Fibreboard III - Foil Facer'), 'fb_m4': (M, 'MEWS Fibreboard IV - Plain'),
            'fb_m5': (M, 'MEWS Fibreboard V - Black Coat'), 'fb_m6': (M, 'MEWS Fibreboard VI - Black Coat'),
            'fb_m7': (M, 'MEWS Fibreboard VII - Black Coat'), 'fb_m8': (M, 'MEWS Fibreboard VIII - Black Coat'),
            'fb_a': (M, 'ASHRAE Fibreboard'),
        },
        refs=('木繊維板', '軟質木繊維板'),
    ),
}

# 厚さ方向の吸水係数 A, kg/(m2 s^0.5)：(下限, 上限, 出典)。液水拡散係数の厚さ方向の目安（Künzel の式）に使う。
# 材料そのものの値がない場合は、同じ種類の材料の値を使う。
_A_PLY_BM = (0.003, 0.003, '建築学会 p53 合板')
_A_PLY_RR = (0.0026, 0.0026, 'RR-110 表 3.5 合板')
_A_OSB_RR = (0.0022, 0.0022, 'RR-110 表 3.5 OSB')
_A_FB_PLAIN = (0.0021, 0.0054, 'RR-110 表 8.4 Plain')
_A_FB_BLACK = (0.00096, 0.0015, 'RR-110 表 8.4 Black Coat')
ABSORPTION = {
    'ply_w1': _A_PLY_BM, 'ply_w2': _A_PLY_BM, 'ply_mews': _A_PLY_RR,
    'ply_a1': _A_PLY_BM, 'ply_a2': _A_PLY_BM, 'ply_a3': _A_PLY_BM,
    'osb_mews': _A_OSB_RR, 'osb_a1': _A_OSB_RR, 'osb_a2': _A_OSB_RR, 'osb_a3': _A_OSB_RR,
    'fb_w': _A_FB_PLAIN, 'fb_m1': (0.0019, 0.0019, 'RR-110 表 8.4 Paper Faced'), 'fb_m2': _A_FB_PLAIN,
    'fb_m4': _A_FB_PLAIN, 'fb_m5': _A_FB_BLACK, 'fb_m6': _A_FB_BLACK, 'fb_m8': _A_FB_BLACK,
    'fb_a': _A_FB_PLAIN,
}

# 熱伝導率と密度の図に重ねる文献（木質ボードの 4 材料すべて）
REFS_LAMBDA = [r for r in REFS if r['property'] == 'lambda_h']


def refs_of(names: tuple[str, ...]) -> list[dict]:
    """文献の材料名が names のどれかと同じか、「名前 + 空白」で始まる行を返す（「木繊維板」と「軟質木繊維板」を区別する）。"""
    return [r for r in REFS if any(r['material'] == n or r['material'].startswith(n + ' ') for n in names)]


def mu_range(refs: list[dict]) -> tuple[float, float]:
    """文献の湿気伝導率から求めた透湿抵抗比 μ の範囲（最小、最大）。"""
    mus = [R.delta_air() / r['value'] for r in refs if r['property'] == 'lambda_dsh_m']
    return min(mus), max(mus)


def plot_mews_plywood_rr110(file_name: str):
    """MEWS Plywood の液水拡散係数を、出典 RR-110 の合板の表（表 3.3）・OSB の表（表 3.4）と、
    建築学会の本の合板の式、厚さ方向の吸水係数からの見積もりと比べる（横軸は含水量 kg/m3）。"""

    import math
    import os
    import sys
    import numpy as np
    sys.path.insert(0, os.path.join(R.HERE, '..', 'mews_check'))
    import rr110_tables as T

    ms = R._materials_by_key()
    ply = ms[(M, 'MEWS Plywood')]
    osb = ms[(M, 'MEWS Oriented Strand Board')]

    fig, ax = R.plt.subplots(figsize=R.ONE_FIGSIZE, layout='constrained')
    ws = np.linspace(5, 620, 300)
    ax.plot(ws, [ply.liquid_diffusivity.d_w(w / ply.rho) for w in ws], color=R.TARGET_COLOR, linewidth=2.4,
            label='Excel の MEWS Plywood（u × 密度 500）', zorder=3)
    ax.plot(ws, [osb.liquid_diffusivity.d_w(w / osb.rho) for w in ws], color=R.SERIES_COLORS[1], linewidth=1.6,
            linestyle='--', label='Excel の MEWS OSB（u × 密度 650）', zorder=2)
    for no, marker, label in ((3, 'o', 'RR-110 表 3.3 合板（小口から吸水）'),
                              (2, 's', 'RR-110 表 3.4 OSB（小口から吸水）')):
        rows = T.DIFFUSIVITY_W_RANGE[no]
        ax.plot([w for w, _, _ in rows], [math.sqrt(lo * hi) for _, lo, hi in rows], linestyle='none', marker=marker,
                markersize=5, markerfacecolor='white', markeredgecolor=R.INK, markeredgewidth=1.1, label=label, zorder=4)
    ax.plot(ws, [3.2e-13 * math.exp(0.015 * w) for w in ws], color=R.INK, linewidth=1.2, linestyle=':',
            label='建築学会 p53 合板の式（Annex 14）', zorder=2)
    # 厚さ方向の目安：Künzel の式（RR-110 表 3.5 の合板の吸水係数 A = 0.0026、wf は MEWS Plywood の RH 99.8% の含水量）
    w_f = R.kunzel_w_f(ply)
    wk = np.linspace(0, w_f, 200)
    ax.plot(wk, [R.kunzel_dws(w, 0.0026, w_f) for w in wk], color=R.INK, linewidth=1.1, linestyle='--', zorder=1,
            label='厚さ方向の目安（Künzel の式、A = 0.0026）')
    ax.set(xlabel='含水量, kg/m3', ylabel='液水拡散係数, m2/s', yscale='log', xlim=(0, 620))
    fig.legend(loc='outside lower center', ncol=2, fontsize=8)
    R._finish(fig, file_name)


def main():

    logging.disable(logging.WARNING)

    ref_ranges = {}
    for group in GROUPS.values():
        refs = refs_of(group['refs'])
        materials = group['materials']
        lo, hi = mu_range(refs)
        for short, target in materials.items():
            others = [key for key in materials.values() if key != target]
            R.plot_one_isotherm(target, others, refs, file_name=f'wood_boards/{short}_u.png')
            R.plot_one_vapour(target, others, refs, file_name=f'wood_boards/{short}_vapour.png')
            R.plot_one_diffusivity(target, others, refs, file_name=f'wood_boards/{short}_dw.png', kunzel=ABSORPTION.get(short))
            R.plot_one_lambda_rho(target, 1, REFS_LAMBDA, file_name=f'wood_boards/{short}_lambda.png')
            ref_ranges[target] = (lo, hi, '・'.join(group['refs']))
        print(f"{'・'.join(group['refs'])}: 文献の μ の範囲 {lo:.3g}〜{hi:.3g}")

    all_materials = [key for group in GROUPS.values() for key in group['materials'].values()]
    R.plot_mu(all_materials, ref_ranges=ref_ranges, file_name='wood_boards/summary_mu.png')
    R.plot_lambda_rho(refs=REFS, highlight=1, title='', file_name='wood_boards/summary_lambda_rho.png')

    plot_mews_plywood_rr110('wood_boards/ply_mews_dw_rr110.png')


if __name__ == '__main__':
    main()
