# docs/reference

材料物性のデータ（Excel）がどう作られたかを、出典の文献と照らし合わせたレポートとスクリプト。

| ファイル | 中身 |
|---|---|
| `mews_excel_derivation.md`（.pdf） | `modules/materials_mews_ashrae.xlsx` の MEWS の材料（No.1〜42）と、出典 RR-110 の照合 |
| `mews_check/` | MEWS の照合スクリプトと出力 |
| `ashrae_excel_derivation.md`（.pdf） | 同じ Excel の ASHRAE の材料（No.43〜80）と、Kumaran (2006) の照合 |
| `ashrae_check/` | ASHRAE の照合スクリプトと出力 |
| `papers/` | 文献（PDF など）。**このリポジトリには入っていない**（下の説明） |

## 文献のフォルダ `papers/`

文献には著作権があるので、公開リポジトリのこのリポジトリには入れない（`.gitignore` で除外している）。
文献は非公開リポジトリ `HydroThermal-references` に入れ、`docs/reference/papers/` に clone して使う。

文献の入手先は、2 つのレポートの 2 章「出典資料の入手先」に書いてある。

### 最初の 1 台目（非公開リポジトリを作る）

1. GitHub で非公開（Private）のリポジトリ `HydroThermal-references` を作る（README などは作らず、空のまま）。
2. 文献を `docs/reference/papers/` に置き、そのフォルダで次を実行する。

```
cd docs/reference/papers
git init
git add .
git commit -m "文献を追加"
git branch -M main
git remote add origin https://github.com/HisashiMiura/HydroThermal-references.git
git push -u origin main
```

### 2 台目以降（clone する）

HydroThermal のフォルダで次を実行する。

```
git clone https://github.com/HisashiMiura/HydroThermal-references.git docs/reference/papers
```

### ふだんの使い方

- 文献を足したときは、`docs/reference/papers/` の中で `git add`・`git commit`・`git push` する。
- もう 1 台では、`docs/reference/papers/` の中で `git pull` する（HydroThermal 側の `git pull` では文献は更新されない）。
