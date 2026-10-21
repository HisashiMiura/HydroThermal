"""⑧ シート・紙類のレビューの図を描き、figures/sheets/ に保存する。

文献の値は、建築学会の本・最新建築環境工学（ref_data/sheets.csv）と、MEWS のメンブレンは出典 RR-110 の表 4.2（mews_check/rr110_tables.py）。
MEWS のメンブレンは平衡含水率・液水拡散係数が 0 なので、湿気伝導率の図だけを描く（熱物性はまとめの図で見る）。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_sheets.py
"""

import logging
import os
import sys

import review_lib as R

sys.path.insert(0, os.path.join(R.HERE, '..', 'mews_check'))
import rr110_tables as T  # noqa: E402

REFS = R.read_refs('sheets.csv')

M = 'mews_ashrae'

# 湿気伝導率の図に重ねる文献（紙・フェルト系と高分子系の両方。MEWS のメンブレンは種類がわからないので全部を重ねる）
VAPOUR_REFS = [r for r in REFS if r['property'] == 'lambda_dsh_m']

# MEWS のメンブレン：図の短い名前: (材料名, 表 4.1 の No, 表 4.2 の列)
# 列は mews_check の照合で決めたもの（RH によらず一定の製品は、その一定値）。
MEMBRANES = {
    'mem_1a': ('MEWS Building Membrane IA', 4, 1.06e-09), 'mem_2': ('MEWS Building Membrane II', 5, 'A'),
    'mem_3': ('MEWS Building Membrane III', 6, 'B'), 'mem_4a': ('MEWS Building Membrane IVA', 7, 2.87e-09),
    'mem_5a': ('MEWS Building Membrane V A', 8, 'D'), 'mem_5c': ('MEWS Building Membrane V C', 9, 'F'),
    'mem_6': ('MEWS Building Membrane VI', 10, 'G'), 'mem_7': ('MEWS Building Membrane VII', 11, 2.37e-09),
    'mem_8': ('MEWS Building Membrane VIII', 12, 1.07e-09), 'mem_9': ('MEWS Building Membrane IX', 13, 2.77e-10),
}

# ASHRAE のシート：図の短い名前: 材料名
ASHRAE = {
    'felt15': 'ASHRAE #15 Felt', 'paper10': 'ASHRAE 10 min Paper', 'paper30': 'ASHRAE 30 min Paper',
    'paper60': 'ASHRAE 60 min Paper', 'spo': 'ASHRAE Spun Bonded Polyolefin Membrane',
    'spo_c': 'ASHRAE Bonded Polyolefin Membrane (Crinkled )',
}

# 吸水係数 A, kg/(m2 s^0.5)（RR-110 4 章：紙系 0.0005〜0.001、高分子系 0.0003 未満）。Künzel の目安に使う。
_A_PAPER = (0.0005, 0.001, 'RR-110 4 章 紙系')
_A_POLYMER = (0.0003, 0.0003, 'RR-110 4 章 高分子系の上限')
ABSORPTION = {'felt15': _A_PAPER, 'paper10': _A_PAPER, 'paper30': _A_PAPER, 'paper60': _A_PAPER,
              'spo': _A_POLYMER, 'spo_c': _A_POLYMER}


def membrane_refs(no: int, column) -> list[dict]:
    """RR-110 表 4.2 のパーミアンスに表 4.1 の厚さをかけた透湿率を、read_refs と同じ形の行にする。"""
    thickness = T.MEMBRANE[no][1] / 1000
    if isinstance(column, float):
        points = [(rh, column) for rh in range(10, 101, 10)]
        note = f'一定 {column:.3g} × 厚さ'
    else:
        points = [(rh, p) for rh, p in T.MEMBRANE_VARIABLE_PERMEANCE[column] if rh > 0]
        note = 'パーミアンス × 厚さ'
    return [dict(doc='RR-110', page='', table='表 4.2', material=f'No.{no} の表', property='lambda_dsh_m',
                 x=rh, value=p * thickness, note=note) for rh, p in points]


def main():

    logging.disable(logging.WARNING)

    mem_keys = [(M, name) for name, _, _ in MEMBRANES.values()]
    ash_keys = [(M, name) for name in ASHRAE.values()]
    ref_ranges = {}

    for short, (name, no, column) in MEMBRANES.items():
        target = (M, name)
        own = membrane_refs(no, column)
        others = [k for k in mem_keys if k != target]
        R.plot_one_vapour(target, others, VAPOUR_REFS + own, file_name=f'sheets/{short}_vapour.png')
        mus = [R.delta_air() / r['value'] for r in own]
        ref_ranges[target] = (min(mus), max(mus), '')

    paper_u = [r for r in REFS if r['property'] == 'u']
    for short, name in ASHRAE.items():
        target = (M, name)
        # 紙・フェルト系と高分子系（ポリオレフィン）で、灰色に描く仲間を分ける
        group = ('spo', 'spo_c') if short.startswith('spo') else ('felt15', 'paper10', 'paper30', 'paper60')
        others = [(M, ASHRAE[g]) for g in group if g != short]
        R.plot_one_isotherm(target, others, paper_u, file_name=f'sheets/{short}_u.png')
        R.plot_one_vapour(target, others, VAPOUR_REFS, file_name=f'sheets/{short}_vapour.png')
        R.plot_one_diffusivity(target, others, (), file_name=f'sheets/{short}_dw.png', kunzel=ABSORPTION.get(short))
        R.plot_one_lambda_rho(target, 8, (), file_name=f'sheets/{short}_lambda.png')

    R.plot_mu(mem_keys + ash_keys, ref_ranges=ref_ranges, file_name='sheets/summary_mu.png')
    R.plot_lambda_rho(highlight=8, title='', file_name='sheets/summary_lambda_rho.png')


if __name__ == '__main__':
    main()
