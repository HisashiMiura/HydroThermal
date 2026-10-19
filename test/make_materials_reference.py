"""Material の計算結果を基準値ファイルに保存する。

Material の中身を書き換える前に、今の計算結果を記録しておくためのスクリプト。
test_materials_reference.py は、この基準値と計算結果が一致することを確認する。

実行方法（プロジェクトのフォルダで）:
    python -m test.make_materials_reference

計算結果を意図して変えたときだけ、実行し直すこと。
"""

import csv
import os

from modules.material_loaders import load_whamcavity
from modules.thermo_dynamics import get_wp


# 基準値ファイル
REFERENCE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'materials_whamcavity_reference.csv')

# 記録する相対湿度, %
# 0% は、軽量モルタルの式（r**-0.120）が計算できないため含めない。
RHS = list(range(1, 100))

# get_dpsi_dmu を計算するときの温度, K
T = 293.15

# 列名
COLUMNS = ['name', 'rh', 'u', 'lambda_dsh_m', 'dpsi_dmu', 'c_rho']


def calculate_rows() -> list[dict]:
    """今の Material で計算した値を、1行 = 1材料・1相対湿度の形で返す。"""

    rows = []

    for m in load_whamcavity():
        for rh in RHS:
            rows.append({
                'name': m.name,
                'rh': rh,
                'u': m.get_u(rh),
                'lambda_dsh_m': m.get_lambda_dsh_m(rh),
                'dpsi_dmu': m.get_dpsi_dmu(mu=get_wp(rh, T), t=T),
                'c_rho': m.c_rho,
            })

    return rows


def read_reference() -> dict:
    """基準値ファイルを読み込む。

    Returns:
        {(材料名, 相対湿度): {列名: 値}}
    """

    with open(REFERENCE_FILE, encoding='utf-8', newline='') as f:
        return {
            (row['name'], int(row['rh'])): {c: float(row[c]) for c in COLUMNS[2:]}
            for row in csv.DictReader(f)
        }


def main():

    rows = calculate_rows()

    os.makedirs(os.path.dirname(REFERENCE_FILE), exist_ok=True)

    # 小数は repr で書き出す（読み込んだときに、元の値と完全に同じ値に戻る書き方）
    with open(REFERENCE_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([row['name'], row['rh']] + [repr(float(row[c])) for c in COLUMNS[2:]])

    print(f'{len(rows)} 行を書き出しました: {REFERENCE_FILE}')


if __name__ == '__main__':
    main()
