# 液相水分伝導率の換算に掛ける密度について（Whamcavity の SUBROUTINE DIFF）

2026-10-24 · Hisashi Miura

## 要旨

SUBROUTINE DIFF は、液水拡散係数 $D_w$ から液相水分伝導率 $\lambda'_{\mu l}$ を求めるときに、水の密度 998 kg/m³ を掛けています。液水拡散係数の出典（ASHRAE RP-1018、NRC の RR-110）の定義と、熱水分同時移動の式の導き方からは、掛けるのは材料の乾燥密度 $\rho_s$ ではないかと考えています。そうであれば、構造用合板の液相水分伝導率は今の値の約 0.6 倍（乾燥密度 600 kg/m³ の場合）になります。Python への移植の中で気づいたので、確認をお願いできればと思います。

## 該当箇所

Whamcavity.f95 の SUBROUTINE DIFF（構造用合板の液相水分伝導率）です。

```fortran
CALL AHGANS(WD,RH,K)
IF(WD>45.AND.WD<110)THEN
  D1=WD*0.01
  DW=EXP(-30.91+4.2967*D1-0.22017*D1*D1)
  RH1=RH+0.005
  RH2=RH-0.005
  CALL REWPT(RH1,WP1,TMP,RG)
  CALL REWPT(RH2,WP2,TMP,RG)
  CALL AHGANS(WD1,RH1,K)
  CALL AHGANS(WD2,RH2,K)
  RML=998.*DW*ABS((WD1-WD2)*0.01/(WP1-WP2))
ELSE
  RML=0.
END IF
```

- 式にすると $\lambda'_{\mu l} = 998 \times D_w \times |\Delta u / \Delta \mu|$ です（$u$：質量含水率 kg/kg、$\mu$：水分化学ポテンシャル J/kg）。
- $D_w$ の式（座標は $u$、範囲 $0.45 < u < 1.10$）は、ASHRAE RP-1018 の Plywood（ASHRAE Plywood-1）の液水拡散係数と同じ係数です。
- 呼び出し側では、構造用合板（材料番号 5）で RH > 90% のときだけこの DIFF を呼び、それ以外の材料では液相水分伝導率を 0 にしています。

## 根拠

出典の定義と式の導き方のどちらからも、掛けるのは材料の乾燥密度になります。

**1. 出典の定義**

NRC の報告書 RR-110（MEWS、式 (5)）と、ASHRAE RP-1018 の概要（Kumaran 2006、式 (5)）は、どちらも液水拡散係数を次の式で定義しています。

$$
J_l = -\rho_0 \, D_w \, \nabla u
$$

$\rho_0$ は乾燥した材料の密度、$u$ は質量含水率 kg/kg、$D_w$ の単位は m²/s です。DIFF の $D_w$ の式は RP-1018 の Plywood の値なので、同じ定義と考えられます。

**2. 式の導き方**

容積あたりの含水量 $w = \rho_s u$（kg/m³）の勾配で液水が流れるとすると、水分化学ポテンシャルの勾配に対する液相水分伝導率は次のようになります。

$$
J_l = -D_w \frac{\partial w}{\partial x} = -D_w \frac{\partial w}{\partial \mu} \frac{\partial \mu}{\partial x}
\quad \Rightarrow \quad
\lambda'_{\mu l} = D_w \frac{\partial w}{\partial \mu} = \rho_s D_w \frac{\partial u}{\partial \mu} = \rho_w D_w \frac{\partial \psi}{\partial \mu}
$$

水の密度 $\rho_w$ を掛けてよいのは、容積含水率 $\psi$（m³/m³）で微分する場合です。DIFF は質量含水率 $u$（AHGANS の値を 0.01 倍した kg/kg）で微分しているので、掛けるのは乾燥密度 $\rho_s$ になります。

## 影響の大きさ

液相水分伝導率は $\rho_s / \rho_w$ 倍（$\rho_w$ = 998 kg/m³）になります。Whamcavity で液水を動かしているのは構造用合板だけなので、今の計算で影響するのは構造用合板の高湿域（RH 90% 超、含水率 0.45〜1.10 kg/kg）です。

| 材料 | 乾燥密度 $\rho_s$, kg/m³ | 今の値に対する倍率 $\rho_s / \rho_w$ |
| --- | --- | --- |
| 構造用合板（Whamcavity の材料データ） | 600 | 0.60 |
| 構造用合板（RP-1018 の Plywood-1） | 445 | 0.45 |

他の材料に液水拡散係数を入れた場合も、同じ式で密度の影響が出ます。例えばグラスウール（10〜30 kg/m³）では 0.01〜0.03 倍、コンクリート（約 2200 kg/m³）では約 2.2 倍です。

## 修正案

998 を、その材料の乾燥密度に置き換える案です。

```fortran
RML=GMA(K)*DW*ABS((WD1-WD2)*0.01/(WP1-WP2))
```

GMA(K) は材料 K の乾燥密度（Whamcavity で密度を持っている配列の名前に合わせてください）。Python 版では、材料の乾燥密度を掛ける形に直す予定です。

## 確認したいこと

1. DIFF の $D_w$ の式（$\exp(-30.91 + 4.2967u - 0.22017u^2)$）は、RP-1018 の Plywood の値でよいでしょうか。別の出典や、容積含水率の勾配で定義した値であれば、水の密度を掛けるのが正しいことになります。
2. 掛ける密度は、Whamcavity の構造用合板の密度（600 kg/m³）と、拡散係数の出典の Plywood-1 の密度（445 kg/m³）のどちらがよいでしょうか。
3. 998 を掛けたのに、何か理由（拡散係数の合わせ込みなど）があったでしょうか。
