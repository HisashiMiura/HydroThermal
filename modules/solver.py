"""時間を 1 ステップ進める：熱と水分を一緒に解く（設計の文書 2.8 節、docs/governing_equations.md 6 章）。

熱と水分の収支の残差（balance.py）を、汎用のニュートン法（newton.py）で 0 にして、次の時刻の状態を作る。
"""

import numpy as np

from modules.balance import heat_residual_is, moisture_residual_is
from modules.boundary import IndoorBoundary, OutdoorBoundary
from modules.newton import newton_solve
from modules.thermo_dynamics import RW
from modules.wall_geometry import WallGeometry
from modules.wall_state import WallState

# ヤコビ行列の帯の幅（下 3 本・上 3 本）：未知数を (T_0, μ_0, T_1, μ_1, …) と並べると、
# 質点 i の熱と水分の残差は、質点 i - 1・i・i + 1 の T と μ（左右に 3 つずつ離れた列まで）にしか関係しない
HEAT_MOISTURE_BAND = (3, 3)

# 熱の残差の許容値, W/m2（温度にすると、およそ 10^-7 K の精度）
HEAT_RESIDUAL_TOL = 1.0e-6

# 水分の残差の許容値, kg/(m2 s)（潜熱にすると熱の許容値と同じ大きさ：tol_h / r）
MOISTURE_RESIDUAL_TOL = HEAT_RESIDUAL_TOL / RW


def step(
        geometry: WallGeometry,
        state_n: WallState,
        dt: float,
        outdoor: OutdoorBoundary,
        indoor: IndoorBoundary
    ) -> tuple[WallState, int]:
    """熱と水分を一緒に 1 ステップ進める。

    未知数を (T_0, μ_0, T_1, μ_1, …) と並べ、熱と水分の残差をそれぞれの許容値で割って（許容値の何倍かにして）、
    交互に並べた残差が 0 になるように、ニュートン法で求める（許容値 1）。最初の仮の値は前の時刻の状態。
    最初の仮の値の残差が許容値より小さくても、1 回は修正する（平衡の近くで、1 ステップの変化が小さいと進まなくなるのを防ぐ）。
    μ ≤ 0（相対湿度 100% 以下）を守る仕組みは、まだ入れていない（段階 5-8）。

    Args:
        geometry: 壁の形
        state_n: 前の時刻（ステップ n）の状態
        dt: 時間刻み, s
        outdoor: 次の時刻の外気の境界条件
        indoor: 次の時刻の室内の境界条件

    Returns:
        次の時刻の状態、ニュートン法の修正の回数
    """

    # 未知数の並び x_ps を、温度と水分化学ポテンシャルに分けて、許容値で割った残差を交互に並べて返す関数（この 1 ステップ専用）
    def residual(x_ps: np.ndarray) -> np.ndarray:

        # 温度は 0 番目から 1 つおき、水分化学ポテンシャルは 1 番目から 1 つおき
        t_is, mu_is = x_ps[0::2], x_ps[1::2]

        res_h_is = heat_residual_is(
            geometry, t_is, mu_is, state_n.t_is, dt, outdoor, indoor) / HEAT_RESIDUAL_TOL
        res_m_is = moisture_residual_is(
            geometry, t_is, mu_is, state_n.t_is, state_n.mu_is, dt, outdoor, indoor) / MOISTURE_RESIDUAL_TOL

        # 熱と水分の残差を交互に並べる
        f_ps = np.empty(len(x_ps))
        f_ps[0::2], f_ps[1::2] = res_h_is, res_m_is
        return f_ps

    # 前の時刻の状態を、(T_0, μ_0, T_1, μ_1, …) の順に並べて、最初の仮の値にする
    x0_ps = np.empty(2 * len(state_n))
    x0_ps[0::2], x0_ps[1::2] = state_n.t_is, state_n.mu_is

    # 残差が 0（許容値の 1 倍以下）になる未知数を探す（1 回は必ず修正する）
    x_ps, m = newton_solve(residual, x0_ps, band=HEAT_MOISTURE_BAND, tol=1.0, min_iter=1)

    return WallState(t_is=x_ps[0::2], mu_is=x_ps[1::2]), m
