"""① 木質ボードのレビューの図を描き、figures/ に保存する。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_figures_wood_boards.py
"""

import logging

import review_lib as R

# 文献の数値（建築学会の本 p51〜59、エース 表 7.2）
REFS = R.read_refs('wood_boards.csv')

W = 'whamcavity'
M = 'mews_ashrae'

# 図ごとの材料と、重ねる文献の材料（ref_data の material 列の先頭が一致するもの）
GROUPS = {
    'plywood': dict(
        title='① 木質ボード：合板',
        materials=[(W, '構造用合板1'), (W, '構造用合板2'), (M, 'MEWS Plywood'),
                   (M, 'ASHRAE Plywood -1'), (M, 'ASHRAE Plywood -2'), (M, 'ASHRAE Plywood -3')],
        refs=('合板',),
    ),
    'osb': dict(
        title='① 木質ボード：OSB（文献はウエハーボードとパーティクルボード）',
        materials=[(M, 'MEWS Oriented Strand Board'), (M, 'ASHRAE OSB -1'), (M, 'ASHRAE OSB -2'), (M, 'ASHRAE OSB -3')],
        refs=('ウエハーボード', 'パーティクルボード'),
    ),
    'fibreboard1': dict(
        title='① 木質ボード：繊維板（その 1）',
        materials=[(W, '軟質繊維版'), (M, 'MEWS Fibreboard I - Paper Facer'), (M, 'MEWS Fibreboard II - Plain'),
                   (M, 'MEWS Fibreboard III - Foil Facer'), (M, 'MEWS Fibreboard IV - Plain'), (M, 'ASHRAE Fibreboard')],
        refs=('木繊維板', '軟質木繊維板'),
    ),
    'fibreboard2': dict(
        title='① 木質ボード：繊維板（その 2、Black Coat）',
        materials=[(M, 'MEWS Fibreboard V - Black Coat'), (M, 'MEWS Fibreboard VI - Black Coat'),
                   (M, 'MEWS Fibreboard VII - Black Coat'), (M, 'MEWS Fibreboard VIII - Black Coat')],
        refs=('木繊維板', '軟質木繊維板'),
    ),
}


def refs_of(prefixes: tuple[str, ...]) -> list[dict]:
    """文献の材料名が prefixes のどれかで始まる行を返す（「木繊維板」と「軟質木繊維板」のように区別する）。"""
    return [r for r in REFS if any(r['material'] == p or r['material'].startswith(p + ' ') for p in prefixes)]


def mu_range(refs: list[dict]) -> tuple[float, float]:
    """文献の湿気伝導率から求めた透湿抵抗比 μ の範囲（最小、最大）。"""
    mus = [R.delta_air() / r['value'] for r in refs if r['property'] == 'lambda_dsh_m']
    return min(mus), max(mus)


def main():

    logging.disable(logging.WARNING)

    ref_ranges = {}
    for key, g in GROUPS.items():
        refs = refs_of(g['refs'])
        R.plot_moisture(g['materials'], refs=refs, title=g['title'], file_name=f'wood_boards_{key}.png')
        lo, hi = mu_range(refs)
        for m in g['materials']:
            ref_ranges[m] = (lo, hi, '・'.join(g['refs']))

    materials = [m for g in GROUPS.values() for m in g['materials']]
    R.plot_mu(materials, ref_ranges=ref_ranges, title='① 木質ボード：透湿抵抗比 μ', file_name='wood_boards_mu.png')

    R.plot_lambda_rho(refs=REFS, highlight=1, title='熱伝導率と密度（① 木質ボードを強調、黒い印は文献）',
                      file_name='wood_boards_lambda_rho.png')

    for key, (lo, hi, name) in {g: ref_ranges[GROUPS[g]['materials'][0]] for g in GROUPS}.items():
        print(f'{key}: 文献（{name}）の μ の範囲 {lo:.3g}〜{hi:.3g}')


if __name__ == '__main__':
    main()
