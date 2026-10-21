"""⑥ 発泡系断熱材のレビューの図を描き、figures/foam_insulation/ に保存する。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_foam_insulation.py
"""

import logging

import review_lib as R

# 文献の数値（建築学会の本 p73〜74・p78〜84）
REFS = R.read_refs('foam_insulation.csv')

W = 'whamcavity'
M = 'mews_ashrae'

GROUPS = {
    'ps': dict(materials={'eps_a': (M, 'ASHRAE Expanded Polystyrene Insulation'), 'xps_a': (M, 'ASHRAE Extruded Polystyrene Insulation'),
                          'foam1_w': (W, '発泡プラスチック1'), 'foam2_w': (W, '発泡プラスチック2'), 'foam3_w': (W, '発泡プラスチック3')},
               refs=('EPS', 'XPS')),
    'pu': dict(materials={'spf_mews': (M, 'MEWS Spray Polyurethane Foam'), 'spf_a': (M, 'ASHRAE Spray Polyurethane Foam Insulation'),
                          'pir_a': (M, 'ASHRAE Polyisocyanurate Insulation'), 'lspf_a': (M, 'ASHRAE Low-density Polyurethane Foam Insulation')},
               refs=('ポリウレタン', 'ポリイソシアヌレート')),
}

# 液水拡散係数の図の横軸の右端（RH 100% の含水率がありえないほど大きい材料）
U_MAX = {'xps_a': 1.0, 'pir_a': 1.0, 'spf_a': 1.0, 'eps_a': 1.0}


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
            R.plot_one_isotherm(target, others, refs, file_name=f'foam_insulation/{short}_u.png')
            R.plot_one_vapour(target, others, refs, file_name=f'foam_insulation/{short}_vapour.png')
            R.plot_one_diffusivity(target, others, refs, file_name=f'foam_insulation/{short}_dw.png', u_max=U_MAX.get(short))
            R.plot_one_lambda_rho(target, 6, [r for r in REFS if r['property'] == 'lambda_h'], file_name=f'foam_insulation/{short}_lambda.png')
        mus = [R.delta_air() / r['value'] for r in refs if r['property'] == 'lambda_dsh_m']
        for k in keys:
            ref_ranges[k] = (min(mus), max(mus), '')

    all_keys = [k for g in GROUPS.values() for k in g['materials'].values()]
    R.plot_mu(all_keys, ref_ranges=ref_ranges, file_name='foam_insulation/summary_mu.png')
    R.plot_lambda_rho(refs=REFS, highlight=6, title='', file_name='foam_insulation/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
