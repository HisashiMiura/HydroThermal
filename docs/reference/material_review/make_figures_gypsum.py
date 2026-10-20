"""③ 石膏ボードのレビューの図を描き、figures/gypsum/ に保存する。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_gypsum.py
"""

import logging

import review_lib as R

# 文献の数値（建築学会の本 p41〜44・p89、エース 表 7.2）
REFS = R.read_refs('gypsum.csv')

W = 'whamcavity'
M = 'mews_ashrae'

MATERIALS = {
    'gyp_w': (W, '石膏ボード'), 'gyp_mews': (M, 'MEWS Exterior Grade Gypsum Board'),
    'gyp_a': (M, 'ASHRAE Gypsum'), 'gyp_a_primer': (M, 'ASHRAE Gypsum + Primer'),
    'gyp_a_latex': (M, 'ASHRAE Gypsum + Primer + Latex'),
}

# 厚さ方向の吸水係数：普通のせっこうボードは手元の文献にない。
# Exterior Grade は RR-110 11 章の「Across the facers ≈ 0.001」。
# wf は平衡含水率が 0 なので、建築学会 p42 の毛細管飽和含水率 400 kg/m3 を使う。
ABSORPTION = {'gyp_mews': (0.001, 0.001, 'RR-110 11 章 Exterior Grade 面材を通して', 400.0)}


def main():

    logging.disable(logging.WARNING)

    for short, target in MATERIALS.items():
        others = [key for key in MATERIALS.values() if key != target]
        R.plot_one_isotherm(target, others, REFS, file_name=f'gypsum/{short}_u.png')
        R.plot_one_vapour(target, others, REFS, file_name=f'gypsum/{short}_vapour.png')
        R.plot_one_diffusivity(target, others, REFS, file_name=f'gypsum/{short}_dw.png', kunzel=ABSORPTION.get(short))
        R.plot_one_lambda_rho(target, 3, [r for r in REFS if r['property'] == 'lambda_h'], file_name=f'gypsum/{short}_lambda.png')

    mus = [R.delta_air() / r['value'] for r in REFS if r['property'] == 'lambda_dsh_m' and r['material'] != '塗装したせっこうボード（換算）' and '耐火板' not in r['note']]
    lo, hi = min(mus), max(mus)
    print(f'文献（塗装なし、耐火板を除く）の μ の範囲 {lo:.3g}〜{hi:.3g}')
    R.plot_mu(list(MATERIALS.values()), ref_ranges={k: (lo, hi, '') for k in MATERIALS.values()}, file_name='gypsum/summary_mu.png')
    R.plot_lambda_rho(refs=REFS, highlight=3, title='', file_name='gypsum/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
