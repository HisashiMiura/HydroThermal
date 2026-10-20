"""全材料の指標を計算して indicators.csv に書き出し、気になる点のある材料を表示する。

実行方法（プロジェクトのフォルダで）:
    python docs/reference/material_review/make_indicators.py
"""

import csv
import logging
import math
import os

from review_lib import HERE, INDICATOR_COLUMNS, CATEGORIES, load_all, indicators

OUTPUT = os.path.join(HERE, 'indicators.csv')


def _format(value) -> str:
    """CSV に書く文字列。小数は有効数字 4 桁、NaN は空欄。"""
    if isinstance(value, float):
        return '' if math.isnan(value) else f'{value:.4g}'
    return str(value)


def main():

    # ローダーのログ（No.27・No.80 の WARNING など）は、ここでは表示しない
    logging.disable(logging.WARNING)

    rows = [indicators(source, m) for source, m in load_all()]

    with open(OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(INDICATOR_COLUMNS.keys())
        for row in rows:
            writer.writerow(_format(row[c]) for c in INDICATOR_COLUMNS)

    print(f'{len(rows)} 材料の指標を書き出しました: {OUTPUT}')
    print()

    print('## カテゴリごとの材料の数')
    for category, name in CATEGORIES.items():
        members = [r for r in rows if r['category'] == category]
        print(f'  {category} {name}: {len(members)}')
    print()

    print('## 「その他」の材料')
    for r in rows:
        if r['category'] == 0:
            print(f"  {r['source']} {r['name']}  密度 {r['rho']:g}  λ {r['lambda_h']:g}  u(80%) {_format(r['u80'])}  μ(50%) {_format(r['mu50'])}")
    print()

    print('## 気になる点のある材料')
    for r in rows:
        if r['flags']:
            print(f"  {r['source']} {r['name']}: {r['flags']}")


if __name__ == '__main__':
    main()
