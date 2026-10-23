"""収支の計算：つながりごとの流れと、質点ごとの残差（設計の文書 2.8 節）。

物理（流れと収支）はここに書く。解く部分（ニュートン法）は物理を知らない汎用の部品にする。
"""

import numpy as np

from modules.wall_geometry import WallGeometry


def heat_flow_ks(geometry: WallGeometry, t_is: np.ndarray, t_outdoor: float, t_indoor: float) -> np.ndarray:
    """つながりごとの熱の流れ q_k, W/m2, [k]（外気側から室内側へ流れる向きを正）。

    q_k = (T_k^左 - T_k^右) / R_k。つながり k は質点 k - 1 と質点 k の間（0 番目は外気と質点 0、最後は最後の質点と室内）。
    水蒸気が運ぶ潜熱と液水が運ぶ熱は、熱と水分を一緒に解くとき（段階 5）に足す。

    Args:
        geometry: 壁の形
        t_is: 各質点の温度, K, [i]
        t_outdoor: 外気温, K
        t_indoor: 室温, K
    """

    # 各つながりの熱抵抗 R_k, (m2 K)/W, [k]
    r_h_ks = np.array([link.r_h for link in geometry.links])

    # つながり k の左の温度, K, [k]（0 番目は外気、それ以外は質点 k - 1）
    t_left_ks = np.concatenate(([t_outdoor], t_is))

    # つながり k の右の温度, K, [k]（最後は室内、それ以外は質点 k）
    t_right_ks = np.concatenate((t_is, [t_indoor]))

    return (t_left_ks - t_right_ks) / r_h_ks


def heat_residual_is(geometry: WallGeometry, t_is: np.ndarray, t_n_is: np.ndarray, dt: float,
                     t_outdoor: float, t_indoor: float) -> np.ndarray:
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
        t_outdoor: 次の時刻の外気温, K
        t_indoor: 次の時刻の室温, K
    """

    # 各質点の熱容量 C_i, J/(m2 K), [i]
    c_is = np.array([node.heat_capacity for node in geometry.nodes])

    # 各つながりの熱の流れ q_k, W/m2, [k]（次の時刻の温度で計算する：後退差分）
    q_ks = heat_flow_ks(geometry, t_is, t_outdoor, t_indoor)

    # 質点 i の左のつながり（つながり i）から入ってくる熱, W/m2, [i]（q_ks の最後を除く）
    q_in_is = q_ks[:-1]

    # 質点 i の右のつながり（つながり i + 1）へ出ていく熱, W/m2, [i]（q_ks の先頭を除く）
    q_out_is = q_ks[1:]

    # たまる量 -（入ってくる熱 - 出ていく熱）
    return c_is * (t_is - t_n_is) / dt - (q_in_is - q_out_is)
