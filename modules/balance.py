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
