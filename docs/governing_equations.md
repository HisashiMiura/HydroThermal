# 熱・水分同時移動の式

作成: 2026-10-24
目的: このプログラムで解く熱と水分の式を、導き方から整理する。水蒸気の流れは水蒸気圧の差で表す（偏微分で温度と水分化学ポテンシャルに分けない）。設計の文書（`design/class_structure.md`）2.8 節の「解き方」の物理の部分にあたる。

---

## 1. 前提

1. 壁の厚さ方向の 1 次元の問題とする。
2. 材料の中の水分は、液水と水蒸気の 2 つの相で保持される。氷は扱わない。
3. 材料の中の各点で、液水と水蒸気は常に平衡している（局所平衡）。そのため、水分の状態は 1 つの量（水分化学ポテンシャル μ）で表せる。
4. 材料は均質で、方向による違いがない。
5. 平衡含水率に吸放湿の履歴はない（相対湿度が決まれば含水率が 1 つに決まる）。
6. 空気の圧力は一定で、材料の中を空気は流れない（通気層の換気は別に扱う）。
7. 液水の流れのうち、温度差による流れと重力による流れは扱わない（重力は、水平方向に流れる壁では効かない）。
8. 熱伝導率は含水率によらない一定値とする。
9. 相変化熱（蒸発潜熱）は温度によらない一定値とする。

---

## 2. 状態量

未知数は、各点の**温度 T** [K] と**水分化学ポテンシャル μ** [J/kg] の 2 つ。ほかの量はこの 2 つから決まる。

| 量 | 式 | 単位 |
|---|---|---|
| 相対湿度 | $\varphi = \exp\left(\dfrac{\mu}{R_v T}\right)$ | − |
| 飽和水蒸気圧 | $p_{sat}(T)$（温度の関数） | Pa |
| 水蒸気圧 | $p_v = \varphi \, p_{sat}(T)$ | Pa |
| 水蒸気の密度 | $\rho_v = \dfrac{p_v}{R_v T}$ | kg/m³ |
| 質量含水率 | $u = u(\varphi)$（平衡含水率の式） | kg/kg |
| 容積あたりの含水量 | $w = \rho_s \, u$ | kg/m³ |
| 容積含水率 | $\psi = w / \rho_w$ | m³/m³ |

- $R_v$：水蒸気の気体定数（461.5 J/(kg K)）、$\rho_s$：材料の乾燥密度 [kg/m³]、$\rho_w$：水の密度 [kg/m³]。
- 水分化学ポテンシャルは、自由水面（相対湿度 100%）を 0 とし、それより乾いた状態では負になる（μ ≤ 0）。

---

## 3. 流れ

外気側から室内側へ向かう x 軸をとり、その向きを流れの正とする。

**熱伝導**

$$
q = -\lambda \frac{\partial T}{\partial x} \tag{3.1}
$$

λ：熱伝導率 [W/(m K)]

**水蒸気の流れ**（水蒸気圧の差で流れる）

$$
J_v = -\lambda'_p \frac{\partial p_v}{\partial x} \tag{3.2}
$$

$\lambda'_p$：湿気伝導率（透湿率）[kg/(m s Pa)]。相対湿度によって変わる。

**液水の流れ**（水分化学ポテンシャルの差で流れる）

$$
J_l = -\lambda'_{\mu l} \frac{\partial \mu}{\partial x} \tag{3.3}
$$

$\lambda'_{\mu l}$：水分化学ポテンシャル勾配に対する液相水分伝導率 [kg/(m s (J/kg))]。液水拡散係数 $D_w$ [m²/s]（含水量 w の勾配に対する値）とは、次の関係にある。

$$
J_l = -D_w \frac{\partial w}{\partial x} = -D_w \frac{\partial w}{\partial \mu} \frac{\partial \mu}{\partial x}
\quad\Rightarrow\quad
\lambda'_{\mu l} = D_w \frac{\partial w}{\partial \mu} = \rho_s D_w \frac{\partial u}{\partial \mu} = \rho_w D_w \frac{\partial \psi}{\partial \mu} \tag{3.4}
$$

**水分の流れ**は、水蒸気と液水の和 $J = J_v + J_l$ [kg/(m² s)]。

---

## 4. 収支式の導き方

「たまる量の変化 ＝ 正味で入ってくる量 ＋ 発生する量」を、液水・水蒸気・エネルギー（エンタルピー）それぞれについて書く。

### 4.1 水分の収支

液水から水蒸気（または逆）への相変化の量を、W [kg/(m³ s)]（水蒸気が液水になる向きを正）とする。

液水の収支：
$$
\frac{\partial (\rho_w \psi)}{\partial t} = -\frac{\partial J_l}{\partial x} + W \tag{4.1}
$$

水蒸気の収支（空隙のうち液水で満たされていない部分 $\Phi_0 - \psi$ に水蒸気がある。$\Phi_0$：乾燥時の空隙率）：
$$
\frac{\partial \{(\Phi_0 - \psi) \rho_v\}}{\partial t} = -\frac{\partial J_v}{\partial x} - W \tag{4.2}
$$

2 つを足すと、相変化の量 W が消えて、水分の収支になる。

$$
\frac{\partial}{\partial t}\left\{ \rho_w \psi + (\Phi_0 - \psi)\rho_v \right\} = -\frac{\partial}{\partial x}(J_v + J_l) \tag{4.3}
$$

### 4.2 熱の収支

材料の実質部・液水・水蒸気のエンタルピーの収支を書き、液水と水蒸気の収支式（4.1・4.2）を使って整理すると、次の式になる（参考文献 [1]）。

$$
c\rho \, \frac{\partial T}{\partial t} = -\frac{\partial q}{\partial x} + r W \tag{4.4}
$$

- $c\rho$：水分を含んだ材料のみかけの容積比熱 [J/(m³ K)]
$$
c\rho = c_s \rho_s + c_w \rho_w \psi + c_v \rho_v (\Phi_0 - \psi) \tag{4.5}
$$
（$c_s$・$c_w$・$c_v$：材料の実質部・液水・水蒸気の比熱。$\rho_s$ は材料の乾燥密度で、$c_s \rho_s$ は乾燥した材料の容積比熱）
- $r$：水蒸気が液水になるときの相変化熱 [J/kg]（蒸発潜熱）
- 整理の途中で、水分の流れが運ぶ顕熱の項（$J_v \, c_v \, \partial T/\partial x$ と $J_l \, c_w \, \partial T/\partial x$）が出てくるが、量が非常に小さいので省く。

### 4.3 近似

**近似 1：材料の中の水蒸気の量を、たまる量から省く**

材料の中では、水蒸気の密度は液水の密度よりずっと小さい（$\rho_v \ll \rho_w$）ので、式 4.3 の左辺の水蒸気の分 $(\Phi_0 - \psi)\rho_v$ と、式 4.5 の水蒸気の熱容量を省く。

- 今の材料のデータには空隙率 $\Phi_0$ がないので、この近似は必要でもある。
- **通気層の空気の質点には、この近似を使わない**。空気の質点は液水を持たず（$\psi = 0$）、空隙がすべて空気（$\Phi_0 = 1$）なので、たまる水分は水蒸気 $\rho_v$ だけになる。

**近似 2：相変化の量は、水蒸気の正味の流入から求める**

水蒸気の収支（式 4.2）で、たまる水蒸気の変化を省くと $W = -\partial J_v / \partial x$ になる。これを式 4.4 に入れると、相変化熱の項は「水蒸気が運ぶ潜熱の流れ $r J_v$」の発散になる。

$$
c\rho \, \frac{\partial T}{\partial t} = -\frac{\partial}{\partial x}\left( q + r J_v \right) \tag{4.6}
$$

---

## 5. 最終的に使う式

### 5.1 連続の式

式 4.3（近似 1）と式 4.6 に、流れの式 3.1〜3.3 を入れる。

**水分の収支**

$$
\frac{\partial w}{\partial t} = \frac{\partial}{\partial x}\left( \lambda'_p \frac{\partial p_v}{\partial x} + \lambda'_{\mu l} \frac{\partial \mu}{\partial x} \right) \tag{5.1}
$$

（通気層の空気では、左辺は $\partial \rho_v / \partial t$、右辺の液水の項はない）

**熱の収支**

$$
c\rho \, \frac{\partial T}{\partial t} = \frac{\partial}{\partial x}\left( \lambda \frac{\partial T}{\partial x} + r \lambda'_p \frac{\partial p_v}{\partial x} \right) \tag{5.2}
$$

ここで、$w = \rho_s u(\varphi)$、$\varphi = \exp(\mu / (R_v T))$、$p_v = \varphi \, p_{sat}(T)$、$c\rho = c_s \rho_s + c_w w$。

### 5.2 温度と水分化学ポテンシャルに分けた形との関係

熱・水分同時移動の式は、水蒸気圧の勾配を温度と水分化学ポテンシャルの勾配に分けた形で書かれることも多い（今のコードと Fortran もこの形）。上の式 5.1・5.2 との関係は次のとおり。

$$
\frac{\partial p_v}{\partial x} = \left(\frac{\partial p_v}{\partial \mu}\right)_T \frac{\partial \mu}{\partial x} + \left(\frac{\partial p_v}{\partial T}\right)_\mu \frac{\partial T}{\partial x}
$$

と分けると、

$$
\lambda'_{\mu g} = \lambda'_p \left(\frac{\partial p_v}{\partial \mu}\right)_T, \qquad
\lambda'_{Tg} = \lambda'_p \left(\frac{\partial p_v}{\partial T}\right)_\mu
$$

（水分化学ポテンシャル勾配・温度勾配に対する気相水分伝導率）を使った形になる。

- **連続の式としては同じ**だが、差分にしたとき（6 章）の扱いが違う。分けた形では、隣り合う質点の水蒸気圧の差を、偏微分を使った 1 次の近似で表すことになる。隣どうしの温度や湿度の差が大きい所（防湿層の両側、断熱材の両側、結露しかけている所など）では、その近似の誤差が答えに残る。
- **このプログラムでは、分けずに水蒸気圧の差のまま使う**。偏微分は、ニュートン法で修正の方向を求めるときだけに使い（設計の文書 2.8 節）、答えには入らない。

### 5.3 境界（空気と接する表面）

表面と空気の間の流れは、伝達率で表す。

$$
q_s = \alpha \, (T_a - T_s), \qquad J_{v,s} = \alpha'_p \, (p_{v,a} - p_{v,s}) \tag{5.3}
$$

α：総合熱伝達率 [W/(m² K)]、$\alpha'_p$：湿気伝達率 [kg/(m² s Pa)]、添字 a は空気、s は表面。

- 空気と表面の間では、液水は移動しない（雨は別に扱う。段階 7）。
- 表面のエンタルピーの収支から、表面を通る熱の流れには、水蒸気が運ぶ潜熱 $r J_{v,s}$ も入る。これは、式 5.2 の「熱伝導 ＋ 潜熱の流れ」と同じ形である。
- 日射・夜間放射による表面の熱は、表面の質点に入る熱として足す（段階 6）。

---

## 6. 差分にした式（このプログラムで解く式）

壁を質点に分け、各質点が受け持つ範囲（コントロールボリューム）で収支をとる。質点 i の左のつながりを k ＝ i、右のつながりを k ＝ i + 1 とする（つながり k は質点 k − 1 と k の間。設計の文書 2.3 節）。時間は後退差分（流れを次の時刻の値で計算する）とし、上付きの n は前の時刻の値を表す。

### 6.1 つながりの流れ

つながり k の左右の値を、添字 L・R で表す（端では外気・室内の値）。$R_{h,k}$・$R_{m,k}$・$R_{l,k}$ は、つながり k の熱抵抗・透湿抵抗・液水の抵抗（左の質点から端まで ＋ 境目 ＋ 右の質点から端まで）。

$$
q_k = \frac{T_L - T_R}{R_{h,k}}, \qquad
j_{v,k} = \frac{p_{v,L} - p_{v,R}}{R_{m,k}}, \qquad
j_{l,k} = \frac{\mu_L - \mu_R}{R_{l,k}} \tag{6.1}
$$

- 材料の中の半分の抵抗は、距離 d を使って $d/\lambda$、$d/\lambda'_p$、$d/\lambda'_{\mu l}$。湿気伝導率と液水伝導率は、その側の質点の状態で計算する。
- 境目（表面・層と層・材料と通気層）の抵抗は、入力のコンダクタンスの逆数（熱 $1/\alpha$、湿気 $1/\alpha'_p$）。**境目では液水は移動しない**（$R_{l,k} = \infty$、$j_{l,k} = 0$）。
- 液水伝導率が 0 の所では、液水の抵抗は無限大（$j_l = 0$）。

### 6.2 質点の水分量と熱容量

質点 i が受け持つ幅を $d_i$ [m] とする（壁 1 m² あたりの量にする）。

| | 材料の質点 | 空気の質点 |
|---|---|---|
| 水分量 $W_i$ [kg/m²] | $\rho_s \, u(\varphi_i) \, d_i$ | $\rho_{v,i} \, d_i$ |
| 熱容量 $C_i$ [J/(m² K)] | $(c_s \rho_s + c_w \, \rho_s u(\varphi_i)) \, d_i$ | $c_a \rho_a \, d_i$（空気の容積比熱） |

### 6.3 残差

次の時刻の T・μ（仮の値）を入れて、質点ごとに「たまる量 −（入ってくる量 − 出ていく量）」を計算する。正しい次の時刻の値なら 0 になる。

**水分の残差** [kg/(m² s)]

$$
\mathrm{res}_{m,i} = \frac{W_i - W_i^n}{\Delta t} - \left\{ (j_{v,i} + j_{l,i}) - (j_{v,i+1} + j_{l,i+1}) \right\} \tag{6.2}
$$

**熱の残差** [W/m²]

$$
\mathrm{res}_{h,i} = C_i \, \frac{T_i - T_i^n}{\Delta t} - \left\{ (q_i + r j_{v,i}) - (q_{i+1} + r j_{v,i+1}) \right\} - Q_i \tag{6.3}
$$

$Q_i$：質点 i に外から入る熱 [W/m²]（外表面の日射・夜間放射、通気層の換気など。段階 6・7）。

- 水分は、たまる量を「含水量の変化」で書くので、水分量が厳密に保存される（水分容量 × μ の変化で書く近似は使わない）。
- 熱容量 $C_i$ は、次の時刻の含水量で計算する。
- すべての質点の残差が 0 になる T・μ を、ニュートン・ラフソン法で求める（設計の文書 2.8 節）。

---

## 7. 記号とコードの名前

| 記号 | 意味 | 単位 | コードの名前（配列は添字 i：質点、k：つながり） |
|---|---|---|---|
| T | 温度 | K | `t_is` |
| μ | 水分化学ポテンシャル | J/kg | `mu_is` |
| φ | 相対湿度 | − | `rh_is`（% で持つ） |
| $p_v$ | 水蒸気圧 | Pa | |
| u | 質量含水率 | kg/kg | `Material.get_u` |
| $\rho_s$ | 材料の乾燥密度 | kg/m³ | `Material.rho` |
| $c_s$ | 材料の比熱 | J/(kg K) | `Material.c` |
| λ | 熱伝導率 | W/(m K) | `Material.lambda_h` |
| $\lambda'_p$ | 湿気伝導率 | kg/(m s Pa) | `Material.get_lambda_dsh_m` |
| $\lambda'_{\mu l}$ | 液相水分伝導率 | kg/(m s (J/kg)) | `Material.get_lambda_dsh_mu_l` |
| $R_v$ | 水蒸気の気体定数 | J/(kg K) | `thermo_dynamics.RG`（461.5） |
| r | 相変化熱（蒸発潜熱） | J/kg | `thermo_dynamics.RW`（2.512×10⁶） |
| $c_w$ | 水の比熱 | J/(kg K) | `thermo_dynamics.CPL`（4200） |
| $\rho_w$ | 水の密度 | kg/m³ | `thermo_dynamics.ROW`（998） |
| $q_k$ | つながりの熱の流れ | W/m² | `heat_flow_ks` |
| $C_i$ | 質点の熱容量 | J/(m² K) | `heat_capacity` |
| $\Delta t$ | 時間刻み | s | `dt` |

---

## 参考文献

- [1] 松本衛ほか：新建築学大系 10 環境物理、彰国社、1983
