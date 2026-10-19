"""materials_mews_ashrae.xlsx の ASHRAE の材料（No.43～80）を、手元の資料で確かめられる範囲で調べる。

出典の RP-1018 最終報告書（材料ごとの測定値の表）は手元にない。そのため次の 3 つだけを調べる。
    1. Kumaran (2006)（入手先は ashrae_excel_derivation.md の 2 章）の材料一覧・密度との照合
    2. Excel の中の整合性・もっともらしさ（平衡含水率の上限、液水拡散係数の区間、同じ値の重なり）
    3. 旧 Excel（materials_whamcavity.xlsx）の構造用合板1 との比較

実行方法（プロジェクトのフォルダで）:
    python docs/reference/ashrae_check/check_ashrae.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, '..', 'mews_check'))

from check_mews import read_excel, isotherm, vapour, diffusivity, poly  # noqa: E402

# Kumaran (2006) p.3～5 の材料一覧。{Excel の No: (論文の番号, 論文の名前, 密度 kg/m3, 密度の根拠)}
# 膜状の製品は「単位面積あたりの質量 ÷ 厚さ」で密度を求めた。
PAPER = {
    43: (3, 'Oriented Strand Board-1', 650, '650 ± 30'),
    44: (4, 'Oriented Strand Board-2', 660, '660 ± 30'),
    45: (5, 'Oriented Strand Board-3', 650, '650 ± 30'),
    46: (6, 'Plywood-1', 445, '445 ± 5'),
    47: (7, 'Plywood-2', 470, '470 ± 5'),
    48: (8, 'Plywood-3', 550, '550 ± 5'),
    49: (9, 'Woodfibre Board', 320, '320 ± 10'),
    50: (10, 'Eastern White Cedar', 360, '360 ± 20'),
    51: (11, 'Western Red Cedar', 350, '350 ± 20'),
    52: (12, 'Spruce', 400, '400 ± 50'),
    53: (13, 'Eastern White Pine', 460, '460 ± 60'),
    54: (14, 'Southern Yellow Pine', 500, '500 ± 40'),
    55: (15, 'Composite Wood Siding', 740, '740 ± 30'),
    56: (16, 'Clay Brick', 1980, '1980 ± 30'),
    57: (17, 'Mortar', 1600, '1600 ± 30'),
    58: (18, 'Stucco', 1985, '1985 ± 30'),
    59: (19, 'Fibre Cement', 1380, '1380 ± 40'),
    60: (20, 'Cement Board', 1130, '1130 ± 50'),
    61: (21, 'Limestone', 2500, '2500 ± 100'),
    62: (22, 'Low Density Glass Fibre Batt Insulation', 11.5, '11.5 ± 1.5'),
    63: (23, 'Cellulose Fibre Insulation', 30, '30 ± 4'),
    64: (24, 'Expanded Polystyrene Insulation', 14.8, '14.8 ± 0.2'),
    65: (25, 'Extruded Polystyrene Insulation', 28.6, '28.6 ± 0.2'),
    66: (26, 'Sprayed Polyurethane Foam Insulation', 39, '39 ± 2'),
    67: (27, 'Polyisocyanurate Board Insulation', 26.5, '26.5 ± 0.2'),
    68: (28, 'Low-Density Sprayed Polyurethane Foam Insulation', 7.5, '6.5～8.5 の中央'),
    69: (29, '#15 Felt', 515 / 0.72, '515 g/m2 ÷ 0.72 mm'),
    70: (30, '10 Minute Paper', 170 / 0.20, '170 g/m2 ÷ 0.20 mm'),
    71: (31, '30 Minute Paper', 200 / 0.22, '200 g/m2 ÷ 0.22 mm'),
    72: (32, '60 Minute Paper', 280 / 0.34, '280 g/m2 ÷ 0.34 mm'),
    73: (33, 'Spun Bonded Polyolefin', 65 / 0.14, '65 g/m2 ÷ 0.14 mm（厚さ 0.14～0.15）'),
    74: (34, 'Spun Bonded Polyolefin with Crinkled Surface', 67 / 0.1, '67 g/m2 ÷ 約 0.1 mm'),
    75: (35, 'Vinyl Wallpaper', 170 / 0.205, '170 g/m2 ÷ 0.205 mm'),
    76: (2, 'Interior Gypsum Board', 625, '625 ± 7'),
    77: (36, 'Primer and Two Coats of a Latex Paint on Gypsum Board', None, '密度の記載なし'),
    78: (36, 'Primer and Two Coats of a Latex Paint on Gypsum Board', None, '密度の記載なし'),
    79: (37, 'EIFS Base & Finish Coats', 1140, '約 1140'),
    80: (None, '（論文の一覧にない）', None, ''),
}

RHO_W = 1000.0  # 水の密度, kg/m3（飽和含水率の目安に使う）


def check_density(rows):
    print('## 1. 論文の材料一覧・密度との照合')
    for no in range(43, 81):
        r = rows[no]
        n, name, rho, src = PAPER[no]
        if rho is None:
            print(f'No.{no} {r["name"][:45]:45s} Excel 密度 {r["rho"]} / 論文: {name}（{src}）')
            continue
        print(f'No.{no} {r["name"][:45]:45s} Excel 密度 {r["rho"]} / 論文 No.{n} {rho:.0f}（{src}）  比 {r["rho"] / rho:.3f}')
    print()


def check_basic(rows):
    print('## 2. 比熱・熱伝導率（Excel の値）')
    for no in range(43, 81):
        r = rows[no]
        print(f'No.{no} {r["name"][:45]:45s} 比熱 {r["c"]:6}  熱伝導率 {r["lambda"]}')
    print()


def check_isotherm(rows):
    print('## 3. 平衡含水率の上限（x = 1 の値）と、水で満たせる量の目安（水の密度 ÷ 乾燥密度）')
    for no in range(43, 81):
        r = rows[no]
        a, b, c, d, f, g = r['iso']
        u1 = isotherm(r, 1.0)
        limit = RHO_W / r['rho']
        mark = '  ← 目安を超える' if u1 > limit else ''
        extra = ''
        if r['iso_parameter'] == 2:
            u98 = a * 0.98**b * math.exp(c * (1 - 0.98**d))
            extra = f'  Parameter=2: g − u(0.98) = {g - u98:.2g}'
        print(f'No.{no} {r["name"][:45]:45s} u(1) = {u1:.4g} kg/kg、目安 {limit:.3g}{mark}{extra}')
    same = {}
    for no in range(43, 81):
        same.setdefault(rows[no]['iso'], []).append(no)
    for coeffs, nos in same.items():
        if len(nos) > 1:
            print(f'  平衡含水率の係数が同じ: {nos}  {coeffs}')
    print()


def check_vapour(rows):
    print('## 4. 透湿率（RH 50% と 100% の値、静止空気 約 1.9e-10 と比べる）')
    for no in range(43, 81):
        r = rows[no]
        print(f'No.{no} {r["name"][:45]:45s} δ(0.5) = {vapour(r, 0.5):.3g}  δ(1.0) = {vapour(r, 1.0):.3g}  係数 {r["vapour"]}')
    print()


def check_diffusivity(rows):
    print('## 5. 液水拡散係数の区間（すき間、境目での値の飛び、上限と飽和の目安）')
    constants = {}
    for no in range(43, 81):
        r = rows[no]
        n = r['n_ranges']
        used = r['ranges'][:max(1, min(n, 3))]
        desc = []
        for i, (lo, hi, co) in enumerate(used):
            degree = max((k for k, cc in enumerate(co) if cc), default=0)
            desc.append(f'({lo}～{hi}, {"定数 " + format(math.exp(co[0]), ".2g") if degree == 0 else str(degree) + "次式"})')
            if degree == 0 and co[0]:
                constants.setdefault(round(co[0], 9), []).append(f'No.{no} 区間{i + 1}' if n else f'No.{no}（範囲分け数 0）')
        notes = []
        if n >= 2:
            for i in range(1, min(n, 3)):
                prev_hi = used[i - 1][1]
                lo = used[i][0]
                if lo != prev_hi:
                    notes.append(f'区間{i}の上限 {prev_hi} と区間{i + 1}の下限 {lo} にすき間')
                else:
                    left = math.exp(poly(used[i - 1][2], prev_hi))
                    right = math.exp(poly(used[i][2], prev_hi + 1e-9))
                    if abs(math.log(right / left)) > math.log(1.5):
                        notes.append(f'u={prev_hi} で値が飛ぶ（{left:.2g} → {right:.2g}）')
            top = used[min(n, 3) - 1][1]
            u_sat = isotherm(r, 1.0)
            notes.append(f'最後の上限 {top} / u(1) = {u_sat:.3g}')
        print(f'No.{no} {r["name"][:45]:45s} 範囲分け数 {n}: {" ".join(desc)}  {"; ".join(notes)}')
    print('  定数の値の重なり:')
    for a, where in sorted(constants.items()):
        if len(where) > 1:
            print(f'    a = {a:.9g}（exp(a) = {math.exp(a):.3g}）: {", ".join(where)}')
    print()


def check_plywood(rows):
    print('## 6. 旧 Excel の構造用合板1 と No.46 ASHRAE Plywood -1')
    from modules.material_loaders import load_whamcavity
    from modules.materials import Materials
    m = Materials(load_whamcavity()).get_material('構造用合板1')
    r = rows[46]
    print(f'  密度: 構造用合板1 {m.rho} / No.46 {r["rho"]}')
    print(f'  熱伝導率: 構造用合板1 {m.lambda_h} / No.46 {r["lambda"]}')
    print(f'  比熱: 構造用合板1 {m.c} / No.46 {r["c"]}')
    print(f'  平衡含水率: 構造用合板1 {m.isotherm} / No.46 {r["iso"]}')
    print(f'  湿気伝導率: 構造用合板1 {m.vapor_conductivity} / No.46 {r["vapour"]}')
    print(f'  液水拡散係数: 構造用合板1 {m.liquid_diffusivity} / No.46 {r["ranges"]}')
    worst = max(abs(m.get_u(rh) / isotherm(r, rh / 100) - 1) for rh in range(1, 100))
    print(f'  平衡含水率の差（RH 1～99%）: 最大相対差 {worst:.2g}')
    print()


def main():
    rows = read_excel()
    check_density(rows)
    check_basic(rows)
    check_isotherm(rows)
    check_vapour(rows)
    check_diffusivity(rows)
    check_plywood(rows)


if __name__ == '__main__':
    main()
