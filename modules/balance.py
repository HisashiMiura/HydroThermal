"""収支の計算：つながりごとの流れと、質点ごとの残差（設計の文書 2.8 節）。

物理（流れと収支）はここに書く。解く部分（ニュートン法）は物理を知らない汎用の部品にする。
"""

import numpy as np

from modules.boundary import IndoorBoundary, OutdoorBoundary
from modules.state import State
from modules.wall_geometry import WallGeometry


def heat_flow_ks(
        geometry: WallGeometry,
        t_is: np.ndarray,
        outdoor: OutdoorBoundary,
        indoor: IndoorBoundary
    ) -> np.ndarray:
    """つながりごとの熱の流れ q_k, W/m2, [k]（外気側から室内側へ流れる向きを正）。

    q_k = (T_k^左 - T_k^右) / R_k。つながり k は質点 k - 1 と質点 k の間（0 番目は外気と質点 0、最後は最後の質点と室内）。
    水蒸気が運ぶ潜熱と液水が運ぶ熱は、熱と水分を一緒に解くとき（段階 5）に足す。

    Args:
        geometry: 壁の形
        t_is: 各質点の温度, K, [i]
        outdoor: 外気の境界条件（外気温 outdoor.state.t を使う）
        indoor: 室内の境界条件（室温 indoor.state.t を使う）
    """

    # 各つながりの熱抵抗 R_k, (m2 K)/W, [k]
    r_h_ks = np.array([link.r_h for link in geometry.links])

    # つながり k の左の温度, K, [k]（0 番目は外気、それ以外は質点 k - 1）
    t_left_ks = np.concatenate(([outdoor.state.t], t_is))

    # つながり k の右の温度, K, [k]（最後は室内、それ以外は質点 k）
    t_right_ks = np.concatenate((t_is, [indoor.state.t]))

    return (t_left_ks - t_right_ks) / r_h_ks


def heat_residual_is(
        geometry: WallGeometry,
        t_is: np.ndarray,
        t_n_is: np.ndarray,
        dt: float,
        outdoor: OutdoorBoundary,
        indoor: IndoorBoundary
    ) -> np.ndarray:
    """質点ごとの熱の収支の残差 res_i, W/m2, [i]。

    res_i = C_i (T_i - T_i^n) / Δt - (q_in,i - q_out,i)（たまる量 -（入ってくる熱 - 出ていく熱））。
    q_in,i = q_i（質点 i の左のつながり i から入ってくる熱）、q_out,i = q_(i+1)（右のつながり i + 1 へ出ていく熱）。
    「入る」「出る」は外気側から室内側へ流れる向きで見た言い方で、q が負のときも式はそのまま正しく働く。
    正しい次の時刻の温度を入れると 0 になる。ニュートン法で 0 になる T を探す。

    Args:
        geometry: 壁の形
        t_is: 各質点の次の時刻の温度（仮の値）, K, [i]
        t_n_is: 各質点の前の時刻（ステップ n）の温度, K, [i]
        dt: 時間刻み, s
        outdoor: 次の時刻の外気の境界条件
        indoor: 次の時刻の室内の境界条件
    """

    # 各質点の熱容量 C_i, J/(m2 K), [i]（熱だけの段階では乾燥した値。水の分は熱と水分を一緒に解くとき（5-6）に足す）
    c_is = np.array([node.heat_capacity_dry for node in geometry.nodes])

    # 各つながりの熱の流れ q_k, W/m2, [k]（次の時刻の温度で計算する：後退差分）
    q_ks = heat_flow_ks(geometry, t_is, outdoor, indoor)

    # 質点 i の左のつながり（つながり i）から入ってくる熱, W/m2, [i]（q_ks の最後を除く）
    q_in_is = q_ks[:-1]

    # 質点 i の右のつながり（つながり i + 1）へ出ていく熱, W/m2, [i]（q_ks の先頭を除く）
    q_out_is = q_ks[1:]

    # たまる量 -（入ってくる熱 - 出ていく熱）
    return c_is * (t_is - t_n_is) / dt - (q_in_is - q_out_is)


def _state_left_right_ks(
        t_is: np.ndarray,
        mu_is: np.ndarray,
        outdoor: OutdoorBoundary,
        indoor: IndoorBoundary
    ) -> tuple[list[State], list[State]]:
    """つながり k の左の状態と右の状態の並び, [k]（左の 0 番目は外気、右の最後は室内）。

    Args:
        t_is: 各質点の温度, K, [i]
        mu_is: 各質点の水分化学ポテンシャル, J/kg, [i]
        outdoor: 外気の境界条件
        indoor: 室内の境界条件
    """

    # 各質点の 1 点の状態, [i]
    state_is = [State(t=t_i, mu=mu_i) for t_i, mu_i in zip(t_is, mu_is)]

    # つながり k の左は質点 k - 1（0 番目は外気）、右は質点 k（最後は室内）
    return [outdoor.state] + state_is, state_is + [indoor.state]


def vapour_flow_ks(
        geometry: WallGeometry,
        t_is: np.ndarray,
        mu_is: np.ndarray,
        outdoor: OutdoorBoundary,
        indoor: IndoorBoundary
    ) -> np.ndarray:
    """つながりごとの水蒸気の流れ j_v,k, kg/(m2 s), [k]（外気側から室内側へ流れる向きを正）。

    j_v,k = (p_v,左 - p_v,右) / R_m,k（docs/governing_equations.md の式 6.1）。
    水蒸気圧は、質点の温度と水分化学ポテンシャルから p_v = φ p_sat(T)、φ = exp(μ / (R_v T)) で求める（偏微分に分けない）。
    透湿抵抗は、左右それぞれの側の状態（相対湿度）で計算する。

    Args:
        geometry: 壁の形
        t_is: 各質点の温度, K, [i]
        mu_is: 各質点の水分化学ポテンシャル, J/kg, [i]
        outdoor: 外気の境界条件
        indoor: 室内の境界条件
    """

    # つながり k の左の状態と右の状態, [k]（左の 0 番目は外気、右の最後は室内）
    state_left_ks, state_right_ks = _state_left_right_ks(t_is, mu_is, outdoor, indoor)

    # つながり k の左右の水蒸気圧, Pa, [k]
    p_v_left_ks = np.array([s.p_v for s in state_left_ks])
    p_v_right_ks = np.array([s.p_v for s in state_right_ks])

    # 各つながりの透湿抵抗 R_m,k, (m2 s Pa)/kg, [k]（左右それぞれの側の状態で計算する）
    r_m_ks = np.array([
        link.r_m(s_left, s_right)
        for link, s_left, s_right in zip(geometry.links, state_left_ks, state_right_ks)
    ])

    return (p_v_left_ks - p_v_right_ks) / r_m_ks


def liquid_flow_ks(
        geometry: WallGeometry,
        t_is: np.ndarray,
        mu_is: np.ndarray,
        outdoor: OutdoorBoundary,
        indoor: IndoorBoundary
    ) -> np.ndarray:
    """つながりごとの液水の流れ j_l,k, kg/(m2 s), [k]（外気側から室内側へ流れる向きを正）。

    j_l,k = (μ_左 - μ_右) / R_l,k（docs/governing_equations.md の式 6.1）。
    境目（表面・層と層・材料と通気層）と、液相水分伝導率が 0 の所では、液水の抵抗が無限大なので流れは 0。

    Args:
        geometry: 壁の形
        t_is: 各質点の温度, K, [i]
        mu_is: 各質点の水分化学ポテンシャル, J/kg, [i]
        outdoor: 外気の境界条件
        indoor: 室内の境界条件
    """

    # つながり k の左の状態と右の状態, [k]
    state_left_ks, state_right_ks = _state_left_right_ks(t_is, mu_is, outdoor, indoor)

    # つながり k の左右の水分化学ポテンシャル, J/kg, [k]
    mu_left_ks = np.array([s.mu for s in state_left_ks])
    mu_right_ks = np.array([s.mu for s in state_right_ks])

    # 各つながりの液水の抵抗 R_l,k, (m2 s (J/kg))/kg, [k]（境目と、液相水分伝導率が 0 の所では無限大）
    r_l_ks = np.array([
        link.r_l(s_left, s_right)
        for link, s_left, s_right in zip(geometry.links, state_left_ks, state_right_ks)
    ])

    # 抵抗が無限大のつながりは、差 / 無限大 = 0
    return (mu_left_ks - mu_right_ks) / r_l_ks


def water_amount_is(geometry: WallGeometry, t_is: np.ndarray, mu_is: np.ndarray) -> np.ndarray:
    """各質点の水分量 W_i, kg/m2, [i]（docs/governing_equations.md 6.2 節）。

    Args:
        geometry: 壁の形
        t_is: 各質点の温度, K, [i]
        mu_is: 各質点の水分化学ポテンシャル, J/kg, [i]
    """
    return np.array([
        node.water_amount(State(t=t_i, mu=mu_i))
        for node, t_i, mu_i in zip(geometry.nodes, t_is, mu_is)
    ])


def heat_capacity_is(geometry: WallGeometry, t_is: np.ndarray, mu_is: np.ndarray) -> np.ndarray:
    """各質点の熱容量 C_i, J/(m2 K), [i]（乾燥した材料 ＋ 含まれる水。docs/governing_equations.md 6.2 節）。

    Args:
        geometry: 壁の形
        t_is: 各質点の温度, K, [i]
        mu_is: 各質点の水分化学ポテンシャル, J/kg, [i]
    """
    return np.array([
        node.heat_capacity(State(t=t_i, mu=mu_i))
        for node, t_i, mu_i in zip(geometry.nodes, t_is, mu_is)
    ])
