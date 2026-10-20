"""④ セメント・組積のレビューの図を描き、figures/cement_masonry/ に保存する。

文献の値は、建築学会の本（ref_data/cement_masonry.csv）と、MEWS の材料は出典 RR-110 の表（mews_check/rr110_tables.py）。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_cement_masonry.py
"""

import logging
import os
import sys

import review_lib as R

sys.path.insert(0, os.path.join(R.HERE, '..', 'mews_check'))
import rr110_tables as T  # noqa: E402

REFS = R.read_refs('cement_masonry.csv')

W = 'whamcavity'
M = 'mews_ashrae'

# グループ：材料（図の短い名前: (出どころ, 材料名, RR-110 の No)）、重ねる建築学会の本の材料、吸水係数（Künzel の目安）
GROUPS = {
    'aerated': dict(
        materials={'alc_w': (W, 'ALC', None), 'aerated_mews': (M, 'MEWS Aerated Concrete', 1)},
        refs=('気泡コンクリート', 'Aerated Concrete（RP-1018）', '気泡コンクリート板'),
        absorption=(0.066, 0.128, '建築学会 p30 [8]')),
    'brick': dict(
        materials={'brick1': (M, 'MEWS Brick I - White Concrete Brick', 14), 'brick2': (M, 'MEWS Brick II - Red Matt Clay Brick', 15),
                   'brick3': (M, 'MEWS Brick III - Buff Matt Clay Brick', 16), 'brick4': (M, 'MEWS Brick IV - Textured Coated Clay Brick', 17),
                   'brick5': (M, 'MEWS Brick V - Concrete Brick', 18), 'brick6': (M, 'MEWS Brick VI - Calcium Silicate Brick', 19),
                   'brick_a': (M, 'ASHRAE Clay Brick', None)},
        refs=('レンガ',),
        absorption=(0.112, 0.121, '建築学会 p35 [3][4] NRC')),
    'mortar': dict(
        materials={'lmortar_w': (W, '軽量モルタル', None), 'mortar1s': (M, 'MEWS Mortar 1-S', 20), 'mortar1n': (M, 'MEWS Mortar 1-N', 21),
                   'mortar2s': (M, 'MEWS Mortar 2-S', 22), 'mortar2n': (M, 'MEWS Mortar 2-N', 23), 'mortar_a': (M, 'ASHRAE Mortar', None)},
        refs=('セメントモルタル', 'モルタル'),
        absorption=(0.042, 0.8, '建築学会 p40 [1]')),
    'stucco': dict(
        materials={'stucco_lime': (M, 'MEWS Regular Lime Stucco', 24), 'stucco_port': (M, 'MEWS Regular Portland Stucco', 25),
                   'stucco_acr': (M, 'MEWS Acrylic Stucco', 26), 'stucco_a': (M, 'ASHRAE Stucco', None)},
        refs=('セメントモルタル', 'モルタル', '石灰プラスター'),
        absorption=(0.042, 0.8, '建築学会 p40 [1] モルタル')),
    'other': dict(
        materials={'clay_w': (W, '土壁', None), 'fibrecement_a': (M, 'ASHRAE Fibre Cement Board', None),
                   'cementboard_a': (M, 'ASHRAE Cement Board', None), 'limestone_a': (M, 'ASHRAE Lime Stone', None)},
        refs=('繊維セメント', '砂-石灰石'),
        absorption=None),
}


# 材料そのものの吸水係数 A, kg/(m2 s^0.5)（RR-110 の表）。ここにある材料は、グループの値の代わりにこれを使う。
ABSORPTION_OWN = {
    'aerated_mews': (0.036, 0.036, 'RR-110 2 章'),
    'brick1': (0.0076, 0.0076, 'RR-110 表 5.3'), 'brick2': (0.0268, 0.0268, 'RR-110 表 5.3'),
    'brick3': (0.0012, 0.0012, 'RR-110 表 5.3'), 'brick4': (0.0322, 0.0322, 'RR-110 表 5.3'),
    'brick5': (0.0097, 0.0097, 'RR-110 表 5.3'), 'brick6': (0.0181, 0.0181, 'RR-110 表 5.3'),
    'mortar1s': (0.063, 0.063, 'RR-110 表 6.4'), 'mortar1n': (0.086, 0.086, 'RR-110 表 6.4'),
    'mortar2s': (0.011, 0.011, 'RR-110 表 6.4'), 'mortar2n': (0.016, 0.016, 'RR-110 表 6.4'),
    'stucco_lime': (0.0050, 0.0050, 'RR-110 表 7.3'), 'stucco_port': (0.0123, 0.0123, 'RR-110 表 7.3'),
    'stucco_acr': (0.0074, 0.0074, 'RR-110 表 7.3'),
}


def refs_of(names):
    return [r for r in REFS if any(r['material'] == n or r['material'].startswith(n + ' ') for n in names)]


def rr110_refs(no: int, rho: float) -> list[dict]:
    """RR-110 の表の値（平衡含水率の吸湿・放湿、液水拡散係数）を、read_refs と同じ形の行にする。"""
    rows = []

    def add(page, prop, x, value, note=''):
        rows.append(dict(doc='RR-110', page='', table=page, material=f'No.{no} の表', property=prop, x=x, value=value, note=note))

    side = {'S': '吸湿', 'D': '放湿'}
    if no in T.ISOTHERM:
        for rh, u, kind in T.ISOTHERM[no]:
            if kind in side:
                add('表', 'u', rh, u, side[kind])
    for rows_t, nos in ((T.BRICK_ISOTHERM_ROWS, T.BRICK_NOS), (T.MORTAR_ISOTHERM_ROWS, T.MORTAR_NOS), (T.STUCCO_ISOTHERM_ROWS, T.STUCCO_NOS)):
        if no in nos:
            k = nos.index(no)
            for kind, rh, values in rows_t:
                if kind in side:
                    add('表', 'u', rh, values[k], side[kind])
    if no in T.DIFFUSIVITY_U:
        for u, d in T.DIFFUSIVITY_U[no]:
            add('表', 'dw', u, d)
    for rows_t, nos in ((T.BRICK_DIFFUSIVITY_W, T.BRICK_NOS), (T.MORTAR_DIFFUSIVITY_W, T.MORTAR_NOS), (T.STUCCO_DIFFUSIVITY_W, T.STUCCO_NOS)):
        if no in nos:
            k = nos.index(no)
            for w, values in rows_t:
                if values[k] is not None:
                    add('表', 'dw', w / rho, values[k], '含水量を密度で割った')
    return rows


def main():

    logging.disable(logging.WARNING)
    ms = R._materials_by_key()

    ref_ranges = {}
    for group in GROUPS.values():
        book = refs_of(group['refs'])
        keys = [(s, n) for s, n, _ in group['materials'].values()]
        for short, (source, name, no) in group['materials'].items():
            target = (source, name)
            refs = book + (rr110_refs(no, ms[target].rho) if no else [])
            others = [k for k in keys if k != target]
            R.plot_one_isotherm(target, others, refs, file_name=f'cement_masonry/{short}_u.png')
            R.plot_one_vapour(target, others, refs, file_name=f'cement_masonry/{short}_vapour.png')
            R.plot_one_diffusivity(target, others, refs, file_name=f'cement_masonry/{short}_dw.png', kunzel=ABSORPTION_OWN.get(short, group['absorption']))
            R.plot_one_lambda_rho(target, 4, [r for r in REFS if r['property'] == 'lambda_h'], file_name=f'cement_masonry/{short}_lambda.png')
        mus = [R.delta_air() / r['value'] for r in book if r['property'] == 'lambda_dsh_m']
        if mus:
            for k in keys:
                ref_ranges[k] = (min(mus), max(mus), '')

    all_keys = [(s, n) for g in GROUPS.values() for s, n, _ in g['materials'].values()]
    R.plot_mu(all_keys, ref_ranges=ref_ranges, file_name='cement_masonry/summary_mu.png')
    R.plot_lambda_rho(refs=REFS, highlight=4, title='', file_name='cement_masonry/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
