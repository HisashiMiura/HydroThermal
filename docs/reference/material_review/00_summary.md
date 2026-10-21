# 材料物性レビュー　全体のまとめ

作成: 2026-10-21（Claude Code による調査）
対象: 旧 Excel（`whamcavity`）19 材料と新しい Excel（`mews_ashrae`）81 材料、合わせて 100 材料。8 つのカテゴリに分けた 96 材料をレビューし、残りの 4 材料（7 章）はカテゴリに入れていない。
カテゴリごとのレポート: `01_wood_boards.md`〜`08_sheets.md`。判定の基準・図の見方は `01_wood_boards.md` 2 章、文献の目録は `sources.md`、全材料の指標は `indicators.csv`（`make_indicators.py`）。

この文書は、8 つのレポートの判定を一か所に集め、直す候補を優先度の順に並べたもの。根拠や図は、各行の節のリンク先にある。

---

## 1. 判定の数

96 材料 × 4 物性の判定の数。

| 判定 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 |
|---|---|---|---|---|
| 妥当 | 61 | 34 | 81 | 26 |
| 要注意 | 10 | 30 | 9 | 48 |
| 誤りの疑い | 3 | 7 | 3 | 1 |
| 根拠なし | 22 | 25 | 3 | 21 |

- **湿気伝導率は 96 材料のうち 81 が妥当**。出典（RR-110、RP-1018）の測定値と合い、文献の範囲にも入る。新しい Excel の値は、透湿についてはおおむね信頼できる。
- **平衡含水率は「要注意」と「誤りの疑い」が 37**。出典の測定値に式を当てはめるときに、低湿域や高湿域で外れたものが多い（4 章）。
- **液水拡散係数は「妥当」が 26 だけ**。ただし、この判定は暫定の方式によるもので（`01_wood_boards.md` 2 章、HANDOFF の未決事項 7）、方式を変えると数が大きく変わる。
- **「根拠なし」は、出典で測っていない物性に値が入っているもの**が多い（シート類、EIFS、壁紙、MEWS の一部）。熱物性の 22 のうち 19 は、厚さ 1 mm 以下のシート・壁紙と厚さ 4.5 mm の EIFS で、計算への影響は小さい。

---

## 2. 誤りの疑いのある材料（11 材料）

ありえない値、写し間違い、当てはめの失敗と見られるもの。

| 材料 | 物性 | 内容 | 節 |
|---|---|---|---|
| セルロースファイバー（旧） | 熱・平衡含水率・湿気伝導率 | 熱伝導率が文献の約半分、平衡含水率がグラスウールの式、湿気伝導率が文献の 1/3000（μ 3900）。セルロースではなく防湿性の発泡断熱材のような性質になる | [⑤ 4.1](05_fibrous_insulation.md) |
| サイディング（旧） | 熱・湿気伝導率 | 湿気伝導率 4.17×10⁻¹⁰ が静止空気より大きい（μ 0.46）。パーミアンスに厚さをかけ忘れた可能性。熱伝導率 0.963 はサイディングの約 8 倍 | [⑦ 3.1](07_exterior_finishes.md) |
| 発泡プラスチック3（旧） | 湿気伝導率 | 1.3×10⁻¹⁰（μ 1.5）・比熱 837 がグラスウール2 とほぼ同じ（写し間違いか） | [⑥ 3.5](06_foam_insulation.md) |
| MEWS Plywood | 液水拡散係数 | OSB の表（RR-110 表 3.4）の値が入っている（表の取り違え） | [① 3.3](01_wood_boards.md) |
| MEWS Oriented Strand Board | 平衡含水率 | RH 50% の含水率が出典・文献の約 1/4（当てはめの失敗） | [① 4.1](01_wood_boards.md) |
| MEWS Aerated Concrete | 平衡含水率 | RH 50% の含水率がほぼ 0（文献の 1/1000 以下） | [④ 3.2](04_cement_masonry.md) |
| ASHRAE Eastern White Cedar | 平衡含水率 | RH 80% で 0.58 kg/kg と、木材ではありえない | [② 3.3](02_lumber.md) |
| ASHRAE Fibre Cement Board | 熱 | 熱伝導率 2.5 は文献（0.14〜0.42）の 6〜18 倍（0.25 の打ち間違いか） | [④ 7.2](04_cement_masonry.md) |
| ASHRAE Low-density Glassfibre Batt Insulation (32 kg/m3) | 平衡含水率 | 密度だけを 32 に変えた材料で、RH 100% の含水率が空隙の 2.8 倍 | [⑤ 3.4](05_fibrous_insulation.md) |
| ASHRAE Extruded Polystyrene Insulation | 平衡含水率 | 係数 a〜d が EPS と同じ（写し間違い）。XPS の文献の 30〜60 倍 | [⑥ 3.2](06_foam_insulation.md) |
| ASHRAE Polyisocyanurate Insulation | 平衡含水率 | RH 95% で 0.70、RH 100% で 636 kg/kg（空隙の 17 倍） | [⑥ 4.3](06_foam_insulation.md) |

**旧 Excel の 3 材料（セルロースファイバー、サイディング、発泡プラスチック3）は、今の壁の計算で既定に使われる材料**（`Layer.source` の既定は `whamcavity`）なので、使っている壁があれば影響が大きい。

---

## 3. 直す・確かめることの一覧

各レポートの「直す・確かめること」を優先度で並べた。優先度は、計算への影響の大きさと、誤りがはっきりしているかで付けた。

### 3.1 優先：高（9 件）

| 材料 | すること | 節 |
|---|---|---|
| 構造用合板1（旧） | 熱伝導率 0.16 を文献の 0.09〜0.12 に近い値にするか検討。今の壁の計算で使っている材料で、熱抵抗が 3〜8 割変わる。密度 600 と水分物性の出典（445）の違いも決める | [① 3.1](01_wood_boards.md) |
| MEWS Plywood | 液水拡散係数を合板の値に直す（RR-110 の合板の表で当てはめ直すか、厚さ方向の値にするか） | [① 3.3](01_wood_boards.md) |
| MEWS Oriented Strand Board | 平衡含水率を RR-110 の表の低湿域にも合うように当てはめ直す | [① 4.1](01_wood_boards.md) |
| ASHRAE Eastern White Cedar | 平衡含水率を当てはめ直す（ほかのシーダーや文献の木材の値を使う） | [② 3.3](02_lumber.md) |
| MEWS Aerated Concrete | 平衡含水率を低湿域（RH 50〜90%）にも合うように当てはめ直す | [④ 3.2](04_cement_masonry.md) |
| ASHRAE Fibre Cement Board | 熱伝導率 2.5 を確かめる（0.25 の打ち間違いか）。外装に使うと熱抵抗を 1/10 に見積もる | [④ 7.2](04_cement_masonry.md) |
| セルロースファイバー（旧） | 熱伝導率・比熱・平衡含水率・湿気伝導率を、文献のセルロース（または ASHRAE Cellulose）の値に直す | [⑤ 4.1](05_fibrous_insulation.md) |
| ASHRAE Polyisocyanurate Insulation | 平衡含水率を文献（NRC）で当てはめ直し、RH 100% の値を空隙を超えない値にする | [⑥ 4.3](06_foam_insulation.md) |
| サイディング（旧） | 何のサイディングを想定したか確かめ、木質なら MEWS Siding IV の値に直す | [⑦ 3.1](07_exterior_finishes.md) |

### 3.2 優先：中

| 材料 | すること | 節 |
|---|---|---|
| 構造用合板2（旧） | 湿気伝導率を湿度で変わる式にする。比熱 1300 の根拠を確かめる | [① 3.2](01_wood_boards.md) |
| MEWS Oriented Strand Board | 液水拡散係数は小口からの値（厚さ方向の目安の約 30 倍） | [① 4.1](01_wood_boards.md) |
| MEWS Fibreboard I・V・VI・VIII | 液水拡散係数は小口からの値で、表面の紙・塗装の影響を受けていない | [① 5.2〜5.9](01_wood_boards.md) |
| MEWS Fibreboard II | 平衡含水率を加圧板の値に合わせて当てはめ直すか検討 | [① 5.3](01_wood_boards.md) |
| MEWS Fibreboard III - Foil Facer | 水分物性がすべて 0。使わないか、扱い方を決める | [① 5.4](01_wood_boards.md) |
| 木材（旧） | 湿気伝導率を湿度で変わる式にする。液水拡散係数を入れるか検討 | [② 3.1](02_lumber.md) |
| 集成材（旧） | 熱伝導率 0.14・比熱 1260 の根拠を確かめる。湿気伝導率を湿度で変わる式にする | [② 3.2](02_lumber.md) |
| ASHRAE Southern Yellow Pine | 平衡含水率の低湿域が文献の約 1/3 | [② 3.7](02_lumber.md) |
| 石膏ボード（旧）・ASHRAE Gypsum | 平衡含水率の文献の違い（KU-Leuven と NIST で 10 倍以上）を確かめる。ASHRAE の液水拡散係数が NRC の測定と 4〜5 桁違う | [③ 3.1・3.3](03_gypsum.md) |
| MEWS Exterior Grade Gypsum Board | 平衡含水率が入っていない。使うなら普通のせっこうボードの値を使う | [③ 3.2](03_gypsum.md) |
| ALC（旧） | 高湿の平衡含水率と液水拡散係数を文献に合わせるか検討 | [④ 3.1](04_cement_masonry.md) |
| ASHRAE Low-density Glassfibre Batt Insulation (32 kg/m3) | 使うなら、熱伝導率を密度 32 の値に、RH 100% の含水率を空隙以下に直す | [⑤ 3.4](05_fibrous_insulation.md) |
| ASHRAE Cellulose Insulation | RH 100% の含水率（空隙の 3.7 倍）を直す。液水拡散係数は文献の値を使うか検討 | [⑤ 4.2](05_fibrous_insulation.md) |
| ASHRAE Extruded Polystyrene Insulation | 平衡含水率を XPS の値で当てはめ直す | [⑥ 3.2](06_foam_insulation.md) |
| 発泡プラスチック3（旧） | 湿気伝導率と比熱の根拠を確かめる | [⑥ 3.5](06_foam_insulation.md) |
| MEWS Siding I〜V | 平衡含水率を、真空飽和ではなく表の吸湿・放湿と加圧板の点に合わせて当てはめ直す。Siding I は湿気伝導率も | [⑦ 3.2](07_exterior_finishes.md) |
| MEWS Siding II・IV・V | 液水拡散係数は小口からの値（塗装面からの目安の 50〜240 倍） | [⑦ 3.3](07_exterior_finishes.md) |

### 3.3 優先：低

まとめて書く（個々の内容は各節）。
- **RP-1018 の最終報告書で確かめたいこと**：ASHRAE の合板・OSB・製材・石膏ボード・グラスウールの液水拡散係数の測り方、Western Red Cedar・Spruce・Eastern White Pine の平衡含水率の低湿域、ASHRAE Composite Wood Siding と MEWS Siding V が同じ製品か、紙・フェルト 4 材料の平衡含水率（[①](01_wood_boards.md)・[②](02_lumber.md)・[③](03_gypsum.md)・[⑤](05_fibrous_insulation.md)・[⑦](07_exterior_finishes.md)・[⑧](08_sheets.md)）。最終報告書（No. B-1115.13）は手元にない。
- **出典に値がない物性**：MEWS Spray Polyurethane Foam の平衡含水率、MEWS EIFS の熱物性、ASHRAE EIFS・Vinyl Wallpaper の測っていない物性、MEWS のメンブレン 10 材料の平衡含水率・熱物性（[⑥ 4.1](06_foam_insulation.md)・[⑦ 4〜5 章](07_exterior_finishes.md)・[⑧ 3 章](08_sheets.md)）。
- **RR-110 の液水拡散係数の表と吸水係数の食い違い**：MEWS のレンガ・スタッコ（[④ 4・6 章](04_cement_masonry.md)）。
- **出どころの確認**：軽量モルタル（旧）の熱伝導率 0.522（土壁と同じ値）、土壁（旧）の物性値（国内の文献）、ASHRAE OSB -3・Gypsum の密度と論文の違い（[④ 5.1・7.1](04_cement_masonry.md)、[① 4.4](01_wood_boards.md)、[③ 3.3](03_gypsum.md)）。
- **ポリオレフィンの液水拡散係数**：透湿防水シートなのに RH 98% を超えると液水が動く（[⑧ 5 章](08_sheets.md)）。

---

## 4. カテゴリをまたいで見えたこと

1. **写し間違い・取り違えが多い**：ほかの材料の値がそのまま入っているものが 7 件見つかった。MEWS Plywood の液水拡散係数（OSB の表）、ASHRAE XPS の平衡含水率（EPS の係数）、発泡プラスチック3 の湿気伝導率（グラスウール2）、セルロースファイバー（旧）と発泡プラスチック1〜3 の平衡含水率（グラスウールの式）、MEWS Gypsum の液水拡散係数の欄（使われない欄に MEWS Siding V の区間 1 の値）、ASHRAE EIFS と Western Red Cedar の液水拡散係数（8×10⁻¹⁴ が全桁一致）、ASHRAE の紙・フェルト・壁紙の平衡含水率（a = 1.0996 が共通）。
2. **平衡含水率の当てはめが、測った範囲の外で崩れる**：低湿域で 0 に近くなるもの（MEWS OSB、Aerated Concrete、Brick III）、RH 100% で空隙を超えるもの（ASHRAE Glassfibre 32・Cellulose・Polyisocyanurate、MEWS Fibreboard II・ASHRAE Fibreboard）、真空飽和に合わせて高湿で大きすぎるもの（MEWS Siding I〜V）。式の形（a·x^b·exp(c(1−x^d)) など）が、測定点の少ない範囲で暴れやすい。
3. **液水拡散係数の「方向」の問題**：RR-110 の値は小口から吸水させて測ったもので、厚さ方向の目安より 1〜2 桁（塗装した製品では 2〜3 桁）大きい。RP-1018 の木質の値は逆に目安より 1〜2 桁小さい。壁の計算は厚さ方向なので、どちらを使うかで結果が大きく変わる。判定の方式そのもの（`01_wood_boards.md` 2 章「この判定方式は暫定」）とあわせて決める必要がある。
4. **旧 Excel の吸湿する材料は、液水が動かない設定**（合板 2 種、軟質繊維版、木材、集成材、石膏ボード、ALC、軽量モルタル、土壁、セルロース、サイディング）。結露や雨水の計算では、液水の移動を考えないことになる。湿気伝導率が一定の材料（構造用合板2、木材、集成材）は、高湿で湿気を通しにくすぎる。
5. **新しい Excel の「置いた値」**：RP-1018 の材料では、測った範囲の外の液水拡散係数が 10⁻¹⁶、10⁻¹²、10⁻⁸、10⁻⁶ などの 10 のべき乗ちょうどの値になっている。Excel の a = ln(99999)（「測っていない」の印）と ln(10⁻¹⁶)（実質 0）の使い分けも、`mews_excel_derivation.md`・`ashrae_excel_derivation.md` に書いた。
6. **透湿はおおむね信頼できる**：湿気伝導率は、出典の測定値と合い、文献の範囲にも入るものがほとんど。外れたのは、旧 Excel の一定値の材料と、写し間違いの 3 件（旧セルロース、旧サイディング、発泡プラスチック3）、MEWS の一部（Brick II・Siding I の低湿域）。

---

## 5. ユーザーが決めること

1. **データを直す時期と範囲**：優先度「高」の 9 件だけ先に直すか、全部をまとめて直すか（HANDOFF の未決事項 6）。直すときは、Excel を直すか、ローダーで上書きするか、新しいデータファイルを作るかも決める。
2. **液水拡散係数の判定の方式**（HANDOFF の未決事項 7）：今の方式（厚さ方向の Künzel の目安と RH 99% で比べる）を続けるか、変えるか。変えると 96 材料の液水拡散係数の判定を見直す。
3. **小口からの値（RR-110）をどう使うか**：表のまま使うか、厚さ方向の値に直すか（MEWS の木質ボード・サイディング）。
4. **液水伝導率に直すときの密度**（HANDOFF の未決事項 1）：液水拡散係数の大きさが計算にどう効くかに関わる。
5. **RP-1018 の最終報告書を手に入れるか**：優先度「低」の確認の多くは、この報告書があれば片づく。

---

## 6. 全材料の判定の一覧

### ① 木質ボード（`01_wood_boards.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| 構造用合板1（旧） | 要注意 | 妥当 | 妥当 | 要注意 | 熱伝導率 0.16 は文献（0.09〜0.12）より大きい | [3.1](01_wood_boards.md) |
| 構造用合板2（旧） | 要注意 | 妥当 | 要注意 | 要注意 | 湿気伝導率が一定。比熱 1300 は小さい。液水が動かない | [3.2](01_wood_boards.md) |
| MEWS Plywood | 妥当 | 妥当 | 妥当 | **誤りの疑い** | 液水拡散係数に OSB の測定値が入っている（表の取り違え） | [3.3](01_wood_boards.md) |
| ASHRAE Plywood -1 | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数が厚さ方向の目安の約 1/40 | [3.4](01_wood_boards.md) |
| ASHRAE Plywood -2 | 妥当 | 妥当 | 妥当 | 妥当 | 液水拡散係数は目安の約 1/8（下限に近い） | [3.5](01_wood_boards.md) |
| ASHRAE Plywood -3 | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数が目安の約 1/20 | [3.6](01_wood_boards.md) |
| MEWS Oriented Strand Board | 妥当 | **誤りの疑い** | 妥当 | 要注意 | RH 50% の含水率が文献・出典の約 1/4。液水拡散係数は目安の約 30 倍 | [4.1](01_wood_boards.md) |
| ASHRAE OSB -1 | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数が目安の約 1/70 | [4.2](01_wood_boards.md) |
| ASHRAE OSB -2 | 妥当 | 妥当 | 妥当 | 要注意 | 同上（約 1/55） | [4.3](01_wood_boards.md) |
| ASHRAE OSB -3 | 妥当 | 妥当 | 妥当 | 要注意 | 同上（約 1/60）。密度 600 は論文の 650 と違う | [4.4](01_wood_boards.md) |
| 軟質繊維版（旧） | 妥当 | 妥当 | 妥当 | 要注意 | 液水が動かない設定 | [5.1](01_wood_boards.md) |
| MEWS Fibreboard I - Paper Facer | 妥当 | 妥当 | 要注意 | 要注意 | μ 60〜90 は繊維板の範囲の外（表面の紙）。液水拡散係数は目安の約 50 倍 | [5.2](01_wood_boards.md) |
| MEWS Fibreboard II - Plain | 妥当 | 要注意 | 妥当 | 要注意 | RH 50% の含水率が文献より 2〜5 割低い。RH 100% で 3.25。液水拡散係数は目安の 16〜110 倍 | [5.3](01_wood_boards.md) |
| MEWS Fibreboard III - Foil Facer | 妥当 | **根拠なし** | 要注意 | 根拠なし | 水分物性がすべて 0 | [5.4](01_wood_boards.md) |
| MEWS Fibreboard IV - Plain | 妥当 | 妥当 | 妥当 | 妥当 | 液水拡散係数は目安の 5〜36 倍（上限に近い） | [5.5](01_wood_boards.md) |
| MEWS Fibreboard V - Black Coat | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数は目安の 33〜81 倍 | [5.6](01_wood_boards.md) |
| MEWS Fibreboard VI - Black Coat | 妥当 | 妥当 | 妥当 | 要注意 | 同上（190〜460 倍） | [5.7](01_wood_boards.md) |
| MEWS Fibreboard VII - Black Coat | 妥当 | 妥当 | 妥当 | 根拠なし | 液水は測っていない | [5.8](01_wood_boards.md) |
| MEWS Fibreboard VIII - Black Coat | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数は目安の 130〜330 倍 | [5.9](01_wood_boards.md) |
| ASHRAE Fibreboard | 妥当 | 要注意 | 妥当 | 要注意 | RH 50% の含水率が文献より 2〜5 割低い。RH 100% で 2.71。液水拡散係数は目安の 100 倍以上 | [5.10](01_wood_boards.md) |

### ② 製材・木材（`02_lumber.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| 木材（旧） | 妥当 | 妥当 | 要注意 | 要注意 | 湿気伝導率が一定（高湿で小さすぎる）。液水が動かない | [3.1](02_lumber.md) |
| 集成材（旧） | 要注意 | 妥当 | 要注意 | 要注意 | 熱伝導率 0.14 は繊維直交方向の文献（0.09〜0.1）より 4 割大きい。比熱 1260 は小さい。湿気伝導率が一定（低湿で大きすぎる） | [3.2](02_lumber.md) |
| ASHRAE Eastern White Cedar | 妥当 | **誤りの疑い** | 妥当 | 要注意 | RH 80% で 0.58 kg/kg と、木材ではありえない（当てはめの失敗） | [3.3](02_lumber.md) |
| ASHRAE Western Red Cedar | 妥当 | 要注意 | 要注意 | 要注意 | RH 50% の含水率が文献の約半分。高湿で湿気を通しにくすぎる | [3.4](02_lumber.md) |
| ASHRAE Spruce | 妥当 | 要注意 | 妥当 | 要注意 | RH 50% の含水率が文献（トウヒ）の約 0.4 倍 | [3.5](02_lumber.md) |
| ASHRAE Eastern White Pine | 妥当 | 要注意 | 妥当 | 要注意 | RH 50% の含水率が文献の 0.35〜0.5 倍 | [3.6](02_lumber.md) |
| ASHRAE Southern Yellow Pine | 妥当 | 要注意 | 妥当 | 要注意 | RH 50% の含水率が文献（サザンパイン）の約 1/3 | [3.7](02_lumber.md) |

### ③ 石膏ボード（`03_gypsum.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| 石膏ボード（旧） | 妥当 | 要注意 | 妥当 | 要注意 | 平衡含水率は文献どうしで 10 倍以上違い、大きい方（KU-Leuven）に合わせている。液水が動かない | [3.1](03_gypsum.md) |
| MEWS Exterior Grade Gypsum Board | 妥当 | **根拠なし** | 妥当 | 根拠なし | 平衡含水率・液水拡散係数が入っていない（すべて 0） | [3.2](03_gypsum.md) |
| ASHRAE Gypsum | 妥当 | 要注意 | 妥当 | 要注意 | 平衡含水率は 3.1 と同じ。液水拡散係数が NRC の測定値より 4〜5 桁小さい | [3.3](03_gypsum.md) |
| ASHRAE Gypsum + Primer | 妥当 | 要注意 | 妥当 | 要注意 | 同上 | [3.4](03_gypsum.md) |
| ASHRAE Gypsum + Primer + Latex | 妥当 | 要注意 | 妥当 | 要注意 | 同上。湿気伝導率は塗装の分だけ小さく、文献の塗料の幅の中 | [3.5](03_gypsum.md) |

### ④ セメント・組積（`04_cement_masonry.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| ALC（旧） | 妥当 | 要注意 | 妥当 | 要注意 | RH 95% 以上の含水率が文献の 1/2〜1/6。液水が動かない | [3.1](04_cement_masonry.md) |
| MEWS Aerated Concrete | 妥当 | **誤りの疑い** | 妥当 | 妥当 | RH 50% の含水率がほぼ 0（文献の 1/1000 以下） | [3.2](04_cement_masonry.md) |
| MEWS Brick I - White Concrete Brick | 妥当 | 妥当 | 妥当 | 妥当 |  | [4.1](04_cement_masonry.md) |
| MEWS Brick II - Red Matt Clay Brick | 妥当 | 妥当 | 要注意 | 要注意 | 低湿の湿気伝導率が出典の約 1/5。液水拡散係数が目安の約 1/30 | [4.2](04_cement_masonry.md) |
| MEWS Brick III - Buff Matt Clay Brick | 妥当 | 要注意 | 妥当 | 要注意 | RH 50% の含水率がほぼ 0。液水拡散係数が目安の 1/2000 | [4.3](04_cement_masonry.md) |
| MEWS Brick IV - Textured Coated Clay Brick | 妥当 | 要注意 | 妥当 | 要注意 | 含水率が出典の 5〜56 倍。液水拡散係数が目安の 1/5000 | [4.4](04_cement_masonry.md) |
| MEWS Brick V - Concrete Brick | 妥当 | 妥当 | 妥当 | 妥当 |  | [4.5](04_cement_masonry.md) |
| MEWS Brick VI - Calcium Silicate Brick | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数が目安の約 1/35 | [4.6](04_cement_masonry.md) |
| ASHRAE Clay Brick | 妥当 | 妥当 | 妥当 | 妥当 | 測った範囲より下の液水拡散係数は 10⁻¹⁶ | [4.7](04_cement_masonry.md) |
| 軽量モルタル（旧） | 要注意 | 根拠なし | 妥当 | 要注意 | 熱伝導率が文献の式の約 1.5 倍。液水が動かない | [5.1](04_cement_masonry.md) |
| MEWS Mortar 1-S | 要注意 | 妥当 | 妥当 | 妥当 | 熱伝導率が文献の式の 0.5〜0.8 倍（出典の測定値とは合う） | [5.2](04_cement_masonry.md) |
| MEWS Mortar 1-N | 要注意 | 妥当 | 妥当 | 妥当 | 同上 | [5.3](04_cement_masonry.md) |
| MEWS Mortar 2-S | 要注意 | 要注意 | 妥当 | 妥当 | 同上。RH 50% の吸湿の含水率が出典の 5 倍 | [5.4](04_cement_masonry.md) |
| MEWS Mortar 2-N | 要注意 | 要注意 | 妥当 | 妥当 | 同上 | [5.5](04_cement_masonry.md) |
| ASHRAE Mortar | 要注意 | 妥当 | 妥当 | 要注意 | 熱伝導率が文献の式の約 0.7 倍。液水拡散係数は吸水係数が分からず判定しにくい | [5.6](04_cement_masonry.md) |
| MEWS Regular Lime Stucco | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数は出典の表と合わないが、出典の吸水係数からの目安とは同じ桁（約 17 倍） | [6.1](04_cement_masonry.md) |
| MEWS Regular Portland Stucco | 妥当 | 妥当 | 妥当 | 妥当 | 同上（目安の約 8 倍） | [6.2](04_cement_masonry.md) |
| MEWS Acrylic Stucco | 妥当 | 妥当 | 妥当 | 妥当 | 同上（目安の約 1.6 倍） | [6.3](04_cement_masonry.md) |
| ASHRAE Stucco | 妥当 | 妥当 | 妥当 | 要注意 | 液水拡散係数は吸水係数が分からず判定しにくい | [6.4](04_cement_masonry.md) |
| 土壁（旧） | 根拠なし | 根拠なし | 根拠なし | 要注意 | 比べられる文献がない。液水が動かない | [7.1](04_cement_masonry.md) |
| ASHRAE Fibre Cement Board | **誤りの疑い** | 妥当 | 要注意 | 妥当 | 熱伝導率 2.5 は文献（0.14〜0.42）の 6〜18 倍 | [7.2](04_cement_masonry.md) |
| ASHRAE Cement Board | 妥当 | 要注意 | 妥当 | 要注意 | 繊維セメントの文献と比べた | [7.3](04_cement_masonry.md) |
| ASHRAE Lime Stone | 根拠なし | 根拠なし | 根拠なし | 根拠なし | 比べられる文献がない | [7.4](04_cement_masonry.md) |

### ⑤ 繊維系断熱材（`05_fibrous_insulation.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| グラスウール1（旧） | 妥当 | 要注意 | 妥当 | 妥当 | RH 50% の含水率が文献の約 1/60。RH 98% 超の直線で RH 100% は 1.0 kg/kg | [3.1](05_fibrous_insulation.md) |
| グラスウール2（旧） | 妥当 | 要注意 | 妥当 | 妥当 | 平衡含水率はグラスウール1 と同じ式 | [3.2](05_fibrous_insulation.md) |
| ASHRAE Low-density Glassfibre Batt Insulation | 妥当 | 要注意 | 妥当 | 根拠なし | RH 100% の含水率 87 kg/kg（空隙をちょうど水で満たす量）。液水拡散係数は 10⁻⁸ の丸い値 | [3.3](05_fibrous_insulation.md) |
| ASHRAE Low-density Glassfibre Batt Insulation (32 kg/m3) | 要注意 | **誤りの疑い** | 妥当 | 根拠なし | No.62 の密度だけを 32 に変えた材料。RH 100% の含水率が空隙の 2.8 倍 | [3.4](05_fibrous_insulation.md) |
| セルロースファイバー（旧） | **誤りの疑い** | **誤りの疑い** | **誤りの疑い** | 要注意 | 熱伝導率が文献の約半分、平衡含水率がグラスウールの式、湿気伝導率が文献の 1/3000 | [4.1](05_fibrous_insulation.md) |
| ASHRAE Cellulose Insulation | 妥当 | 要注意 | 妥当 | 要注意 | RH 100% の含水率 122 kg/kg（空隙の 3.7 倍）。液水拡散係数 10⁻⁶ は文献の約 100 倍 | [4.2](05_fibrous_insulation.md) |

### ⑥ 発泡系断熱材（`06_foam_insulation.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| ASHRAE Expanded Polystyrene Insulation | 妥当 | 妥当 | 妥当 | 妥当 | 平衡含水率は文献（Hansen の EPS）とよく合う | [3.1](06_foam_insulation.md) |
| ASHRAE Extruded Polystyrene Insulation | 妥当 | **誤りの疑い** | 妥当 | 妥当 | 平衡含水率の係数 a〜d が EPS と同じで、XPS の文献（NRC）の 30〜60 倍 | [3.2](06_foam_insulation.md) |
| 発泡プラスチック1（旧） | 妥当 | 要注意 | 妥当 | 妥当 | 平衡含水率はグラスウールの式。比熱 1260 は文献 1470 より小さい | [3.3](06_foam_insulation.md) |
| 発泡プラスチック2（旧） | 妥当 | 要注意 | 妥当 | 妥当 | 同上 | [3.4](06_foam_insulation.md) |
| 発泡プラスチック3（旧） | 妥当 | 要注意 | **誤りの疑い** | 妥当 | 湿気伝導率 1.3×10⁻¹⁰（μ 1.5）はグラスウール2 と同じ値で、発泡プラスチックの 10〜100 倍 | [3.5](06_foam_insulation.md) |
| MEWS Spray Polyurethane Foam | 妥当 | **根拠なし** | 妥当 | 妥当 | 平衡含水率が 0（測っていない） | [4.1](06_foam_insulation.md) |
| ASHRAE Spray Polyurethane Foam Insulation | 妥当 | 要注意 | 妥当 | 根拠なし | 平衡含水率が RH 25〜90% でほぼ一定（0.0066）。液水拡散係数は 10⁻¹² の置いた値 | [4.2](06_foam_insulation.md) |
| ASHRAE Polyisocyanurate Insulation | 妥当 | **誤りの疑い** | 妥当 | 根拠なし | RH 95% で 0.70、RH 100% で 636 kg/kg（空隙の 17 倍） | [4.3](06_foam_insulation.md) |
| ASHRAE Low-density Polyurethane Foam Insulation | 根拠なし | 根拠なし | 根拠なし | 根拠なし | 密度 7.5 の連続気泡のフォームで、比べられる文献がない | [4.4](06_foam_insulation.md) |

### ⑦ 外装・仕上げ（`07_exterior_finishes.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| サイディング（旧） | **誤りの疑い** | 要注意 | **誤りの疑い** | 要注意 | 湿気伝導率 4.17×10⁻¹⁰ は静止空気より大きい（μ 0.46）。熱伝導率 0.963 はサイディングの約 10 倍 | [3.1](07_exterior_finishes.md) |
| MEWS Siding I - OSB | 妥当 | 要注意 | 要注意 | 要注意 | 平衡含水率が RH 91% で表の 2.6 倍。湿気伝導率は表の 0.37〜0.99 倍。液水が動かない | [3.2](07_exterior_finishes.md) |
| MEWS Siding II - Plywood | 妥当 | 要注意 | 妥当 | 要注意 | 液水拡散係数は表（小口から吸水）と一致し、厚さ方向の目安の約 240 倍 | [3.3](07_exterior_finishes.md) |
| MEWS Siding III - Fibreboard | 妥当 | 要注意 | 妥当 | 要注意 | 液水が動かない（RR-110 で解析できなかった製品） | [3.4](07_exterior_finishes.md) |
| MEWS Siding IV - Fibreboard | 妥当 | 要注意 | 妥当 | 要注意 | 液水拡散係数は表と一致し、厚さ方向の目安の約 56 倍 | [3.5](07_exterior_finishes.md) |
| MEWS Siding V - Fibreboard | 妥当 | 要注意 | 妥当 | 要注意 | 同上（約 49 倍） | [3.6](07_exterior_finishes.md) |
| ASHRAE Composite Wood Siding | 妥当 | 妥当 | 妥当 | 要注意 | 湿気伝導率が MEWS Siding V と同じ（同じ製品の可能性） | [3.7](07_exterior_finishes.md) |
| MEWS EIFS Base Coat + Finish Coat | **根拠なし** | 妥当 | 妥当 | 妥当 | 水分物性は RR-110 表 10.1 と一致。熱物性は出典に値がなく、比熱 1880 は木材の値 | [4.1](07_exterior_finishes.md) |
| ASHRAE EIFS Base Coat and Finish Coat | **根拠なし** | 根拠なし | 妥当 | 根拠なし | RP-1018 で測ったのは透湿・透気だけ。熱伝導率 0.588 は MEWS EIFS（0.1）の約 6 倍 | [4.2](07_exterior_finishes.md) |
| ASHRAE Vinyl Wallpaper | 根拠なし | 根拠なし | 妥当 | 根拠なし | RP-1018 で測ったのは透湿・透気・吸水だけ。平衡含水率は文献の壁紙と近い | [5.1](07_exterior_finishes.md) |

### ⑧ シート・紙類（`08_sheets.md`）

| 材料 | 熱 | 平衡含水率 | 湿気伝導率 | 液水拡散係数 | 主な点 | 節 |
|---|---|---|---|---|---|---|
| MEWS Building Membrane IA | 根拠なし | 根拠なし | 妥当 | 根拠なし | 湿気伝導率だけ出典の値。ほかは 0 または全製品で同じ値 | [3.1](08_sheets.md) |
| MEWS Building Membrane II | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.2](08_sheets.md) |
| MEWS Building Membrane III | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.3](08_sheets.md) |
| MEWS Building Membrane IVA | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.4](08_sheets.md) |
| MEWS Building Membrane V A | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上（低湿で表の 0.79 倍） | [3.5](08_sheets.md) |
| MEWS Building Membrane V C | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.6](08_sheets.md) |
| MEWS Building Membrane VI | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上（RH 10% だけ表の 0.08 倍）。湿度で透湿が 900 倍変わる膜 | [3.7](08_sheets.md) |
| MEWS Building Membrane VII | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.8](08_sheets.md) |
| MEWS Building Membrane VIII | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.9](08_sheets.md) |
| MEWS Building Membrane IX | 根拠なし | 根拠なし | 妥当 | 根拠なし | 同上 | [3.10](08_sheets.md) |
| ASHRAE #15 Felt | 根拠なし | 根拠なし | 妥当 | 妥当 | 平衡含水率は 4 材料でほぼ同じ曲線（測っていない） | [4.1](08_sheets.md) |
| ASHRAE 10 min Paper | 根拠なし | 根拠なし | 妥当 | 妥当 | 同上 | [4.2](08_sheets.md) |
| ASHRAE 30 min Paper | 根拠なし | 根拠なし | 妥当 | 妥当 | 同上 | [4.3](08_sheets.md) |
| ASHRAE 60 min Paper | 根拠なし | 根拠なし | 妥当 | 妥当 | 同上 | [4.4](08_sheets.md) |
| ASHRAE Spun Bonded Polyolefin Membrane | 根拠なし | 根拠なし | 妥当 | 要注意 | 液水拡散係数は RH 98% より上で 10⁻⁹ 台 | [5.1](08_sheets.md) |
| ASHRAE Bonded Polyolefin Membrane (Crinkled ) | 根拠なし | 根拠なし | 妥当 | 要注意 | 同上（10⁻¹⁰ 台） | [5.2](08_sheets.md) |

---

## 7. レビューしていない材料（4 材料）

カテゴリに入れていない材料（2026-10-21 にユーザーと確認）。物性の比べようがないので判定はしていないが、指標で気づいた点を書いておく。

| 材料 | 出どころ | 気づいた点 |
|---|---|---|
| シージング | 旧 Excel | 中身がわからない。密度・比熱が 0（熱容量なし）。平衡含水率の式は手順 5 で単位と境目を直した。旧 Excel と Fortran で熱伝導率・湿気伝導率が違う（HANDOFF の問題の一覧） |
| サーモプライ | 旧 Excel | 中身がわからない（商品名）。密度 715、比熱 1310、熱伝導率 0.21、湿気伝導率は一定 2.3×10⁻¹¹ |
| 通気層 | 旧 Excel | 空気の層。密度・比熱が 0、熱伝導率 0.0058、湿気伝導率は一定 8.7×10⁻¹²（μ 22）。空気の層の扱い（名前で見分けている）は、プログラムの未決の問題 |
| Air | 新しい Excel | 密度 1.2、比熱 1000、熱伝導率 0.022（静止空気は 20 ℃ で約 0.026）。**湿気伝導率が 0**（RH 50% で 0）。空気の層として使うと湿気を通さない計算になるので、使う前に確かめる |
