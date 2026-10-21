"""⑦ 外装・仕上げのレビューの図を描き、figures/exterior_finishes/ に保存する。

文献の値は、建築学会の本（ref_data/exterior_finishes.csv：壁紙・繊維混入ポリマーセメント・塗料）と、
MEWS の材料は出典 RR-110 の表（mews_check/rr110_tables.py：Siding 9 章、EIFS 10 章）。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_exterior_finishes.py
"""

import logging
import os
import sys

import review_lib as R

sys.path.insert(0, os.path.join(R.HERE, '..', 'mews_check'))
import rr110_tables as T  # noqa: E402

REFS = R.read_refs('exterior_finishes.csv')

W = 'whamcavity'
M = 'mews_ashrae'

# グループ：材料（図の短い名前: (出どころ, 材料名, 重ねる RR-110 の表の No)）、重ねる建築学会の本の材料
# 旧 Excel のサイディングは、平衡含水率が MEWS Siding IV と同じ式なので、No.38 の表を重ねる。
GROUPS = {
    'siding': dict(
        materials={'siding_w': (W, 'サイディング', 38),
                   'siding1': (M, 'MEWS Siding I - OSB', 35), 'siding2': (M, 'MEWS Siding II - Plywood', 36),
                   'siding3': (M, 'MEWS Siding III - Fibreboard', 37), 'siding4': (M, 'MEWS Siding IV - Fibreboard', 38),
                   'siding5': (M, 'MEWS Siding V - Fibreboard', 39), 'siding_a': (M, 'ASHRAE Composite Wood Siding', None)},
        refs=()),
    'eifs': dict(
        materials={'eifs_mews': (M, 'MEWS EIFS Base Coat + Finish Coat', 40),
                   'eifs_a': (M, 'ASHRAE EIFS Base Coat and Finish Coat', 40)},
        refs=('繊維混入ポリマーセメント', 'ストラクチャードペイント')),
    'wallpaper': dict(
        materials={'wallpaper_a': (M, 'ASHRAE Vinyl Wallpaper', None)},
        refs=('壁紙2（ビニル）', '壁紙4（ビニル）')),
}

# 壁紙の湿気伝導率の図には、6 種類すべての壁紙を重ねる
WALLPAPER_ALL = ('壁紙2（ビニル）', '壁紙4（ビニル）', '壁紙1（繊維）', '壁紙3（繊維）', '壁紙5（紙）', '壁紙6（紙）')

# 塗装面からの吸水係数 A, kg/(m2 s^0.5)（RR-110 表 9.2、製品 1〜5）。Künzel の目安に使う。
ABSORPTION = {
    'siding1': (0.00038, 0.00038, 'RR-110 表 9.2'), 'siding2': (0.00047, 0.00047, 'RR-110 表 9.2'),
    'siding3': (0.00058, 0.00058, 'RR-110 表 9.2'), 'siding4': (0.00060, 0.00060, 'RR-110 表 9.2'),
    'siding5': (0.00062, 0.00062, 'RR-110 表 9.2'),
    'siding_w': (0.00060, 0.00060, 'RR-110 表 9.2 製品 4'),
    'siding_a': (0.00038, 0.00062, 'RR-110 表 9.2 製品 1〜5'),
}


def refs_of(names):
    return [r for r in REFS if r['material'] in names]


def rr110_refs(no: int) -> list[dict]:
    """RR-110 の表の値（平衡含水率の吸湿・放湿、湿気伝導率、液水拡散係数、熱伝導率）を、read_refs と同じ形の行にする。

    含水量 kg/m3 の拡散係数の表は、表 9.1 の試料の密度で割って kg/kg にする（旧 Excel のサイディングにも No.38 の表を同じ形で重ねるため）。
    """
    rows = []

    def add(prop, x, value, note=''):
        rows.append(dict(doc='RR-110', page='', table='表', material=f'No.{no} の表', property=prop, x=x, value=value, note=note))

    side = {'S': '吸湿', 'D': '放湿'}
    if no in T.SIDING_NOS:
        k = T.SIDING_NOS.index(no)
        for kind, rh, values in T.SIDING_ISOTHERM_ROWS:
            if kind in side:
                add('u', rh, values[k], side[kind])
        # 表 9.5 はパーミアンスなので、表 9.1 の厚さをかけて透湿率にする
        for rh, p in zip(T.SIDING_RH, T.SIDING_PERMEANCE[no]):
            add('lambda_dsh_m', rh, p * T.SIDING_THICKNESS[no], 'パーミアンス × 厚さ')
    if no in T.SIDING_DIFFUSIVITY_NOS:
        k = T.SIDING_DIFFUSIVITY_NOS.index(no)
        rho = T.DENSITY_CONDUCTIVITY[no][0]
        for w, values in T.SIDING_DIFFUSIVITY_W:
            add('dw', w / rho, values[k], '含水量を表 9.1 の密度で割った')
    if no == 40:
        for rh, u in T.EIFS_ISOTHERM:
            add('u', rh, u)
        for rh, d in T.VAPOUR_PERMEABILITY[40]:
            add('lambda_dsh_m', rh, d)
        for u, d in T.DIFFUSIVITY_U[40]:
            add('dw', u, d)
    if no in T.DENSITY_CONDUCTIVITY:
        rho_t, lam, _ = T.DENSITY_CONDUCTIVITY[no]
        add('lambda_h', rho_t, lam)
    return rows


def main():

    logging.disable(logging.WARNING)
    ms = R._materials_by_key()

    # 熱伝導率と密度の図に重ねる文献：RR-110 のサイディング 5 製品（表 9.1）
    siding_lambda = [dict(doc='RR-110', page='', table='表 9.1', material='Siding 1〜5 の表', property='lambda_h',
                          x=T.DENSITY_CONDUCTIVITY[no][0], value=T.DENSITY_CONDUCTIVITY[no][1], note='')
                     for no in T.SIDING_NOS]

    ref_ranges = {}
    for group_name, group in GROUPS.items():
        book = refs_of(group['refs'])
        keys = [(s, n) for s, n, _ in group['materials'].values()]
        for short, (source, name, no) in group['materials'].items():
            target = (source, name)
            own = rr110_refs(no) if no else []
            refs = book + [r for r in own if r['property'] != 'lambda_h']
            others = [k for k in keys if k != target]
            R.plot_one_isotherm(target, others, refs, file_name=f'exterior_finishes/{short}_u.png')
            vapour_refs = refs_of(WALLPAPER_ALL) if group_name == 'wallpaper' else refs
            R.plot_one_vapour(target, others, vapour_refs, file_name=f'exterior_finishes/{short}_vapour.png')
            mus = [R.delta_air() / r['value'] for r in vapour_refs if r['property'] == 'lambda_dsh_m']
            if mus:
                ref_ranges[target] = (min(mus), max(mus), '')
            R.plot_one_diffusivity(target, others, refs, file_name=f'exterior_finishes/{short}_dw.png', kunzel=ABSORPTION.get(short))
            lambda_refs = siding_lambda if group_name == 'siding' else []
            R.plot_one_lambda_rho(target, 7, lambda_refs, file_name=f'exterior_finishes/{short}_lambda.png')

    all_keys = [(s, n) for g in GROUPS.values() for s, n, _ in g['materials'].values()]
    R.plot_mu(all_keys, ref_ranges=ref_ranges, file_name='exterior_finishes/summary_mu.png')
    R.plot_lambda_rho(refs=siding_lambda, highlight=7, title='', file_name='exterior_finishes/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
