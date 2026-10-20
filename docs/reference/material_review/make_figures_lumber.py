"""② 製材・木材のレビューの図を描き、figures/lumber/ に保存する。

材料ごとに 4 枚（平衡含水率、湿気伝導率、液水拡散係数、熱伝導率と密度）と、まとめの図 2 枚（μ、熱伝導率と密度）。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_lumber.py
"""

import logging

import review_lib as R

# 文献の数値（建築学会の本 p45〜50・p90、エース 表 7.2）
REFS = R.read_refs('lumber.csv')

W = 'whamcavity'
M = 'mews_ashrae'

# 材料（図のファイル名に使う短い名前と、(出どころ, 材料名)）
MATERIALS = {
    'wood_w': (W, '木材'), 'glulam_w': (W, '集成材'),
    'cedar_e': (M, 'ASHRAE Eastern White Cedar'), 'cedar_w': (M, 'ASHRAE Western Red Cedar'),
    'spruce': (M, 'ASHRAE Spruce'), 'pine_e': (M, 'ASHRAE Eastern White Pine'), 'pine_s': (M, 'ASHRAE Southern Yellow Pine'),
}

# 厚さ方向（繊維直交方向）の吸水係数：建築学会 p48 パインの 0.0040 kg/(m2 s^0.5)。ほかの樹種も、この値を使う
ABSORPTION = (0.0040, 0.0040, '建築学会 p48 パイン 繊維直交方向')


def main():

    logging.disable(logging.WARNING)

    for short, target in MATERIALS.items():
        others = [key for key in MATERIALS.values() if key != target]
        R.plot_one_isotherm(target, others, REFS, file_name=f'lumber/{short}_u.png')
        R.plot_one_vapour(target, others, REFS, file_name=f'lumber/{short}_vapour.png')
        R.plot_one_diffusivity(target, others, REFS, file_name=f'lumber/{short}_dw.png', kunzel=ABSORPTION)
        R.plot_one_lambda_rho(target, 2, [r for r in REFS if r['property'] == 'lambda_h'], file_name=f'lumber/{short}_lambda.png')

    # μ の帯：文献の繊維直交方向（と方向の記載のない値）の湿気伝導率から
    mus = [R.delta_air() / r['value'] for r in REFS if r['property'] == 'lambda_dsh_m' and '繊維方向' not in r['note'].replace('繊維直交方向', '')]
    lo, hi = min(mus), max(mus)
    print(f'文献（繊維直交方向・方向の記載なし）の μ の範囲 {lo:.3g}〜{hi:.3g}')
    R.plot_mu(list(MATERIALS.values()), ref_ranges={k: (lo, hi, '') for k in MATERIALS.values()}, file_name='lumber/summary_mu.png')
    R.plot_lambda_rho(refs=REFS, highlight=2, title='', file_name='lumber/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
