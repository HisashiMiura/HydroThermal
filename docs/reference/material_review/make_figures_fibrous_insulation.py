"""⑤ 繊維系断熱材のレビューの図を描き、figures/fibrous_insulation/ に保存する。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_fibrous_insulation.py
"""

import logging

import review_lib as R

# 文献の数値（建築学会の本 p67〜70・p75〜77）
REFS = R.read_refs('fibrous_insulation.csv')

W = 'whamcavity'
M = 'mews_ashrae'

# 液水拡散係数の図の横軸の右端, kg/kg（RH 100% の含水率がありえないほど大きい材料で、文献の範囲が見えるように絞る）
U_MAX = {'cel_a': 8.0, 'gw_a': 1.0, 'gw32_a': 1.0}

GROUPS = {
    'glass': dict(materials={'gw1_w': (W, 'グラスウール1'), 'gw2_w': (W, 'グラスウール2'),
                             'gw_a': (M, 'ASHRAE Low-density Glassfibre Batt Insulation'),
                             'gw32_a': (M, 'ASHRAE Low-density Glassfibre Batt Insulation (32 kg/m3)')},
                  refs=('グラスウール',)),
    'cellulose': dict(materials={'cel_w': (W, 'セルロースファイバー'), 'cel_a': (M, 'ASHRAE Cellulose Insulation')},
                      refs=('セルロース',)),
}


def refs_of(names):
    return [r for r in REFS if any(r['material'] == n or r['material'].startswith(n + ' ') or r['material'].startswith(n + '（') for n in names)]


def main():

    logging.disable(logging.WARNING)

    ref_ranges = {}
    for group in GROUPS.values():
        refs = refs_of(group['refs'])
        keys = list(group['materials'].values())
        for short, target in group['materials'].items():
            others = [k for k in keys if k != target]
            R.plot_one_isotherm(target, others, refs, file_name=f'fibrous_insulation/{short}_u.png')
            R.plot_one_vapour(target, others, refs, file_name=f'fibrous_insulation/{short}_vapour.png')
            R.plot_one_diffusivity(target, others, refs, file_name=f'fibrous_insulation/{short}_dw.png', u_max=U_MAX.get(short))
            R.plot_one_lambda_rho(target, 5, [r for r in REFS if r['property'] == 'lambda_h'], file_name=f'fibrous_insulation/{short}_lambda.png')
        mus = [R.delta_air() / r['value'] for r in refs if r['property'] == 'lambda_dsh_m']
        for k in keys:
            ref_ranges[k] = (min(mus), max(mus), '')

    all_keys = [k for g in GROUPS.values() for k in g['materials'].values()]
    R.plot_mu(all_keys, ref_ranges=ref_ranges, file_name='fibrous_insulation/summary_mu.png')
    R.plot_lambda_rho(refs=REFS, highlight=5, title='', file_name='fibrous_insulation/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
