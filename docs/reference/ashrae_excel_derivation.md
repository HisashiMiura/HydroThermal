# materials_mews_ashrae.xlsx の ASHRAE 材料（No.43〜80）の値はどう作られたか

作成: 2026-10-20（Claude Code による調査）
対象: `modules/materials_mews_ashrae.xlsx` の「データファイル用」シート、材料名が「ASHRAE」で始まる No.43〜80
出典資料: Kumaran (2006)、homepages.doc（入手先は 2 章）
照合スクリプト: `docs/reference/ashrae_check/`（再現方法は 7 章）
関連: MEWS 材料（No.1〜42）は `docs/reference/mews_excel_derivation.md`

---

## 1. まとめ

- **出典**：ASHRAE の材料は、NRC カナダ IRC が行った ASHRAE Research Project 1018（RP-1018）の結果である。最終報告書「A Thermal and Moisture Transport Property Database for Common Building and Insulating Materials」（No. B-1115.13, 2002）が材料ごとの測定値を載せているが、**手元にない**（ASHRAE で販売）。
- **手元の資料で確かめられたこと**：概要論文 Kumaran (2006) にある 37 材料の一覧と密度。Excel の 38 材料のうち 32 材料で、密度が論文と一致した（XPS の丸めを含めると 33 材料）。測定値そのもの（透湿率・平衡含水率・拡散係数の表）は論文にないため、**係数が測定値に合っているかは確かめられない**。
- **論文と合わない、または論文にない材料**：No.45 OSB-3（密度 600、論文 650）、No.65 XPS（28、論文 28.6）、No.76〜78 Gypsum（700、論文 625）、**No.80 Glassfibre（密度 32、論文の一覧にない）**。
- **物理的にありえない値**：平衡含水率の上限（相対湿度 100% の値）が、空隙をすべて水で満たした量の目安を超える材料がある（**No.63 Cellulose 122 kg/kg（目安 33）、No.67 Polyisocyanurate 636 kg/kg（目安 38）、No.80 Glassfibre 87 kg/kg（目安 31）**）。No.59 Fibre Cement Board の熱伝導率 2.5 W/(m·K) も、ほかのセメント系の約 10 倍。
- **液水拡散係数の範囲の作りが MEWS と違う**：ASHRAE の材料は、測った範囲より下の区間を 10⁻¹⁶（実質 0）としている。MEWS は「端の値で一定」として延ばしている。また、9 材料で区間の間にすき間がある（プログラムでは前の区間を延ばして埋める。6 章 3）。
- **旧 Excel の構造用合板1 の出典**：水分の物性（平衡含水率・湿気伝導率・液水拡散係数）は、**No.46 ASHRAE Plywood -1 と一致**した。一方、密度（600 と 445）、熱伝導率（0.16 と 0.092）、比熱（1860 と 1880）は違う。

---

## 2. 調べ方と限界

### 資料
| 資料 | 中身 |
|---|---|
| Kumaran, M.K. (2006) "A Thermal and Moisture Property Database for Common Building and Insulation Materials", ASHRAE Transactions 112(2), pp.1-13（NRCC-45692、NRC Publications Archive） | RP-1018 の概要。37 材料の一覧と密度・厚さ・単位面積あたりの質量、試験方法、液水拡散係数の定義（式(5)）、Aerated Concrete の測定例、物性ごとに測ったかどうかの一覧（Table 9） |
| homepages.doc | IRC Hygrothermal Properties Database の説明。99999 が「測っていない」の印であること |

### 出典資料の入手先
出典資料は他の人が書いたものなので、リポジトリには入れていない。次の場所から入手できる（2026-10-20 に確認）。

- `Kumaran2006_ASHRAE_RP1018_NRCC-45692.pdf`：Kumaran (2006)（NRCC-45692）：https://nrc-publications.canada.ca/eng/view/accepted/?id=63105660-f433-4b32-a1e0-7c2df4372c94
- `homepages.doc`：3 つの部分からなる。
  1. IRC の広報誌 Construction Innovation 第8巻第4号（2003年12月）の記事「Results of IRC's material properties studies now available」（Kumaran）：https://nrc-publications.canada.ca/eng/view/object/?id=0e1e4021-5691-48b9-aeea-825135c95a23
  2. IRC のホームページの文章（データの入手方法）：元の場所は http://irc.nrc-cnrc.gc.ca/bes/hygro/dbase.html 。今は公開されていない（2026-10-20 に探したが見つからなかった）。
  3. IRC Hygrothermal Properties Database（ソフト）の説明書の一部（99999 = 測っていない、透気率の換算方法）：今は公開されていない。

### 調べたこと（`ashrae_check/check_ashrae.py`）
1. 論文の材料一覧・密度と、Excel の密度の照合
2. Excel の中の整合性・もっともらしさ（平衡含水率の上限、透湿率の大きさ、液水拡散係数の区間、ほかの材料と同じ値）
3. 旧 Excel の構造用合板1 との比較

### 限界
- **測定値の照合はできない**：論文には Aerated Concrete 以外の測定値の表がない。透湿率・平衡含水率・液水拡散係数の係数が、測定値に正しく合わせてあるかは分からない。
- **論文の Table 9（測ったかどうかの一覧）は、PDF から取り出すと表の形が崩れていて、材料と Yes/No の対応が読み取れなかった。**
- 「空隙をすべて水で満たした量の目安」には、材料の固体部分の体積を無視して「水の密度 ÷ 乾燥密度」を使った。本当の上限はこれより小さい。そのため、目安を超える値は確実にありえないが、目安を下回るからといって正しいとは言えない。

---

## 3. 出典と対応表（密度の照合）

| Excel の No | 材料 | 論文の番号・名前 | 論文の密度 kg/m³ | Excel の密度 | 一致 |
|---|---|---|---|---|---|
| 43〜45 | OSB -1, -2, -3 | 3〜5 Oriented Strand Board-1〜3 | 650, 660, 650 | 650, 660, **600** | OSB-3 だけ違う |
| 46〜48 | Plywood -1, -2, -3 | 6〜8 Plywood-1〜3 | 445, 470, 550 | 445, 470, 550 | ○ |
| 49 | Fibreboard | 9 Woodfibre Board | 320 | 320 | ○ |
| 50〜54 | Eastern White Cedar, Western Red Cedar, Spruce, Eastern White Pine, Southern Yellow Pine | 10〜14 | 360, 350, 400, 460, 500 | 同じ | ○ |
| 55 | Composite Wood Siding | 15 | 740 | 740 | ○ |
| 56〜58 | Clay Brick, Mortar, Stucco | 16〜18 | 1980, 1600, 1985 | 同じ | ○ |
| 59, 60 | Fibre Cement Board, Cement Board | 19, 20 | 1380, 1130 | 同じ | ○ |
| 61 | Lime Stone | 21 Limestone | 2500 | 2500 | ○ |
| 62 | Low-density Glassfibre Batt | 22 | 11.5 | 11.5 | ○ |
| 63 | Cellulose Insulation | 23 | 30 | 30 | ○ |
| 64, 65 | Expanded / Extruded Polystyrene | 24, 25 | 14.8, 28.6 | 14.8, **28** | XPS は丸め（2%） |
| 66〜68 | Spray PU Foam, Polyisocyanurate, Low-density PU Foam | 26〜28 | 39, 26.5, 6.5〜8.5 | 39, 26.5, 7.5 | ○ |
| 69〜72 | #15 Felt, 10 / 30 / 60 min Paper | 29〜32（質量/面積 ÷ 厚さ） | 715, 850, 909, 824 | 715, 850, 909, 823 | ○ |
| 73, 74 | Spun Bonded Polyolefin（普通、Crinkled） | 33, 34（同上） | 464, 670 | 464, 670 | ○ |
| 75 | Vinyl Wallpaper | 35（同上） | 829 | 829 | ○ |
| 76 | Gypsum | 2 Interior Gypsum Board | 625 | **700** | 違う（MEWS の Exterior Gypsum と同じ 700） |
| 77, 78 | Gypsum + Primer, Gypsum + Primer + Latex | 36 Primer and Two Coats of a Latex Paint on Gypsum Board | 記載なし | 700 | — |
| 79 | EIFS Base Coat and Finish Coat | 37 | 約 1140 | 1140 | ○ |
| 80 | Low-density Glassfibre Batt（2 つ目） | **一覧にない** | — | **32** | — |

膜状の製品（No.69〜75）の密度は、論文の「単位面積あたりの質量 ÷ 厚さ」で計算した値と一致した（例：#15 Felt は 515 g/m² ÷ 0.72 mm = 715 kg/m³）。MEWS のメンブレンと同じ作り方である。

論文の Aerated Concrete（番号 1）は、Excel では MEWS の No.1 として入っている（MEWS の報告書 RR-110 と同じ測定）。

---

## 4. Excel の中の整合性・もっともらしさ

### 4.1 熱伝導率・比熱
- **No.59 Fibre Cement Board の熱伝導率 2.5 W/(m·K)** は、ほかのセメント系（Cement Board 0.255、Stucco 0.41、Mortar 0.47）の約 10 倍で、0.25 の打ち間違いの可能性がある。
- 比熱は材料の種類ごとに同じ値（木質系 1880、セメント・石・れんが系 840、発泡系 1470 など）。論文には「比熱は IEA Annex 24 の値」とある。MEWS では Brick 800、Mortar 900 で、ASHRAE の Clay Brick・Mortar の 840 とは違う。

### 4.2 平衡含水率
相対湿度 100% のときの値（x = 1 の値）を、「空隙をすべて水で満たした量の目安（水の密度 1000 ÷ 乾燥密度）」と比べた。

| 材料 | x = 1 の値 kg/kg | 目安 kg/kg | 見立て |
|---|---|---|---|
| **No.63 Cellulose** | **122.1** | 33.3 | 目安の約 4 倍。ありえない |
| **No.67 Polyisocyanurate** | **635.9** | 37.7 | 目安の約 17 倍。ありえない |
| **No.80 Glassfibre（密度 32）** | **87**（Parameter = 2 の f） | 31.2 | 目安の約 3 倍。No.62（密度 11.5）の f = 87 = 1000 ÷ 11.5 をそのまま写したと見られる |
| No.62 Glassfibre（密度 11.5） | 87（f） | 87.0 | 目安とちょうど同じ。f は「空隙をすべて水で満たした量」として決めたと見られる |
| No.64 EPS, No.65 XPS | 56, 21（f） | 67.6, 35.7 | 目安以下 |
| No.66 Spray PU Foam | 3.88 | 25.6 | 目安以下 |
| No.68 Low-density PU Foam | 0.80 | 133 | 目安よりずっと小さい（液水拡散係数の範囲は 85 kg/kg まで。4.4 節） |
| ほかの材料 | 0.013〜2.7 | — | すべて目安以下 |

ほかに気づいたこと。
- **No.62 と No.80 は、平衡含水率の係数（a〜d、f、g）がすべて同じ**。密度だけが違う。
- No.76 Gypsum と No.78 Gypsum + Primer + Latex は係数がすべて同じ。No.77 Gypsum + Primer だけ少し違う。
- No.69〜72（#15 Felt、10 / 30 / 60 min Paper）と No.75 Vinyl Wallpaper は、x = 1 の値 a がどれも 1.0996（b〜d は違う）。
- No.64 EPS の g が No.65 XPS と同じ値で、No.64 自身の式の x = 0.98 の値と 9×10⁻⁸ ずれている。
- 論文の結論には、「平衡含水率は、ほかの物性ほど詳しくは測れなかった（平衡に時間がかかりすぎた）」とある。平衡含水率の係数は、ほかの物性より根拠が弱い可能性がある。

### 4.3 透湿率
- RH によらず一定の材料：No.62・80 Glassfibre 1.7×10⁻¹⁰（静止空気の値 約 1.9×10⁻¹⁰ に近く、もっともらしい）、No.68 Low-density PU Foam 8.8×10⁻¹¹、No.73・74 Spun Bonded Polyolefin 6.1×10⁻¹³・3.1×10⁻¹³。
- ほかの材料は、RH とともに増える形で、大きさも材料の種類からみて不自然なものはなかった（10⁻¹⁴〜10⁻¹⁰）。測定値との照合はできない。

### 4.4 液水拡散係数

**範囲の作り：MEWS との違い**

| | MEWS | ASHRAE |
|---|---|---|
| 測った範囲より下 | 端の値で一定 | **10⁻¹⁶（実質 0）**（全 36 材料。範囲分け数 0 の EPS・XPS を除く） |
| 測った範囲 | 多項式 | 多項式（主に 2 次・3 次）、または定数 |
| 測った範囲より上 | 端の値で一定 | 定数（範囲分け数 3 の材料） |

そのため、ASHRAE の材料では、区間1 と区間2 の境目で値が大きく飛ぶ。例えば No.46 Plywood -1 は、u = 0.45 で 10⁻¹⁶ から 2.5×10⁻¹³ に、No.63 Cellulose は u = 0.2 で 10⁻¹⁶ から 10⁻⁶ になる。旧 Excel の構造用合板1（Fortran の DIFF）が「含水率 0.45 以下では 0」としているのも、この作りと同じである。

**区間のすき間**（区間1 の上限と区間2 の下限が違う）

| 材料 | 区間1 の上限 | 区間2 の下限 |
|---|---|---|
| No.49 Fibreboard | 0.058 | 0.094 |
| No.62・80 Glassfibre | 0.022 | 0.023 |
| No.66 Spray PU Foam | 0.071 | 0.077 |
| No.67 Polyisocyanurate | 8.1 | 9.3 |
| No.68 Low-density PU Foam | 0.25 | 0.27 |
| No.76〜78 Gypsum（3 種） | 0.13 | 0.15 |

すき間の含水率では、どの区間の式も当てはまらない。プログラムでは、前の区間（区間1、10⁻¹⁶）の上限を次の区間の下限まで延ばして埋める（6 章 3）。

**範囲と平衡含水率の上限が合わない材料**
- No.67 Polyisocyanurate：拡散係数の範囲は 38 kg/kg まで（目安 37.7 と同じ）、平衡含水率の上限は 636。
- No.63 Cellulose：拡散係数の範囲は 30 kg/kg まで、平衡含水率の上限は 122。
- No.68 Low-density PU Foam：拡散係数の範囲は 85 kg/kg まで、平衡含水率の上限は 0.80。
- No.56 Clay Brick：拡散係数の範囲の上限 0.099 が、平衡含水率の上限 0.088 より大きい。

**丸い値の定数と、同じ値の重なり**
- 区間2 が定数だけの材料（Glassfibre 1×10⁻⁸、Cellulose 1×10⁻⁶、Spray PU Foam・Polyisocyanurate・Low-density PU Foam 1×10⁻¹²、Lime Stone 7×10⁻¹¹、EIFS 8×10⁻¹⁴）は、測定値に当てはめた値ではなく、丸めた値を入れたように見える。
- No.46 Plywood -1 と No.48 Plywood -3 の区間3 の定数（3.9×10⁻¹²）は全桁一致する。
- No.51 Western Red Cedar の区間3 と No.79 EIFS の区間2（8×10⁻¹⁴）は全桁一致する。

---

## 5. 旧 Excel の構造用合板1 と No.46 ASHRAE Plywood -1

| 物性 | 構造用合板1（旧 Excel・Fortran） | No.46 ASHRAE Plywood -1 | 一致 |
|---|---|---|---|
| 平衡含水率 | 1.0625·r^1.5373·exp(−1.6471·(1−r^32.051)) | a=1.0625, b=1.5373, c=−1.6471, d=32.051 | **一致**（RH 1〜99% で最大相対差 1.6×10⁻¹⁵） |
| 湿気伝導率 | a=1.87E-11, b=2.4019, c=−0.78864, d=1.1471 | a=1.8742E-11, b〜d 同じ | b〜d は全桁一致、a は丸め |
| 液水拡散係数 | 含水率 0.45〜1.10 で exp(−30.91 + 4.2967u − 0.22017u²)、それ以外は 0 | 区間2（0.45〜1.1）が同じ式。区間1 は 10⁻¹⁶、区間3（1.1〜1.9）は 3.9×10⁻¹² | 区間2 は全桁一致 |
| 乾燥密度 | **600** | **445** | 違う |
| 熱伝導率 | **0.16** | **0.092** | 違う |
| 比熱 | 1860 | 1880 | 違う |

**見立て**：構造用合板1 は、水分の物性を ASHRAE RP-1018 の Plywood-1 から取り、密度・熱物性は別の出典（日本の合板の一般的な値など）から取った「組み合わせ」の材料と考えられる。Fortran のコードにある「*3.45」（湿気伝導率に掛ける係数をコメントアウトしたもの）の理由は、この資料からは分からない。

---

## 6. このプログラムへの影響

1. **液水伝導率に掛ける密度（HANDOFF の未決事項 1）**
   ASHRAE の材料も、液水拡散係数の定義は RR-110 と同じ式(5) `Jl = −ρ0·Dw·grad u` である（Kumaran 2006）。そのため、**掛ける密度は材料の乾燥密度**になる。構造用合板1 の拡散係数も RP-1018 の Plywood-1 から取ったものなので、同じ定義と考えられる。その場合、今の `get_lambda_dsh_mu_l` が掛けている水の密度 998 は、乾燥密度（445 または 600）にすべきことになる。445 と 600 のどちらを使うかは、判断が必要。
2. **区間の外の扱い（2026-10-20 に決定、対応済み）**
   ASHRAE の材料は、測った範囲より下を 10⁻¹⁶（実質 0）、上を定数としている。
   プログラム（`material_loaders._liquid_diffusivity_from_ranges`）では、**最後の区間の後ろに「上限から +∞ まで、上限での値で一定」の区間を足す**（多項式の材料は上限での値を計算して定数にする）。Excel の値は変えていない。RH 100% の平衡含水率が最後の区間の上限より大きく、計算結果が変わるのは 8 材料（MEWS の No.28、ASHRAE の No.49・58・63・66・67・73・74）で、これらはログに出す。理由：測った範囲より上を「端の値で一定」とする Excel の作り方に合い、上限で値が急に変わらず、範囲の外で多項式を使わないため（0 にすると RH 100% 近くで液水が急に動かなくなる。式をそのまま延ばすと No.49 では 10⁻⁸¹ まで下がる）。
3. **区間のすき間（2026-10-20 に決定、対応済み）**：9 材料（No.49・62・66・67・68・76・77・78・80）で、すき間の含水率ではどの区間の式も当てはまらない。
   プログラム（`material_loaders._liquid_diffusivity_from_ranges`）では、**前の区間の上限を次の区間の下限まで延ばして埋める**（例：No.76 Gypsum の区間1「〜0.13」を「〜0.15」とする）。埋めたときは材料名と値をログに出す。Excel の値は変えていない。
   理由：ASHRAE の材料は測った範囲（区間2）より下をすべて 10⁻¹⁶ としていて、すき間も測った範囲より下にあたるため。次の区間を下に延ばすと、測った範囲の外で多項式を使い、測っていない液水移動を作ってしまう。すき間の値は 0 から 10⁻¹⁶ に変わるだけなので、計算結果はほとんど変わらない。
4. **使うときに注意が必要な材料**：No.63 Cellulose・No.67 Polyisocyanurate・No.80 Glassfibre の平衡含水率、No.59 Fibre Cement Board の熱伝導率。

---

## 7. 再現方法

```bash
# プロジェクトのフォルダで
python docs/reference/ashrae_check/check_ashrae.py
```

- `ashrae_check/check_ashrae.py`：論文の材料一覧・密度（ファイルの中に書き写してある）との照合と、Excel の中の整合性の確認
- `ashrae_check/output.txt`：このレポートを書いたときの出力
- 式の計算には `mews_check/check_mews.py` の関数（中でプログラムの部品 `modules/material_props.py` を使う）を使っている

RP-1018 の最終報告書（No. B-1115.13）が手に入れば、`mews_check/` と同じ形で、測定値の表との照合ができる。
