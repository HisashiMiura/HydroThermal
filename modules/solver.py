"""時間を 1 ステップ進める（設計の文書 2.8 節）。

収支の残差（balance.py）を、汎用のニュートン法（newton.py）で 0 にして、次の時刻の状態を作る。
段階 4 では熱だけ（水分化学ポテンシャルは変えない）。段階 5 で、熱と水分を一緒に解く 1 ステップに広げる。
"""

from modules.balance import heat_residual_is
from modules.newton import newton_solve
from modules.wall_geometry import WallGeometry
from modules.wall_state import WallState

# 熱だけを解くときのヤコビ行列の帯の幅（下 1 本・上 1 本）：質点 i の熱の残差は、自分と左右の隣の温度だけに関係する
HEAT_BAND = (1, 1)

# 熱の残差の許容値, W/m2（温度にすると、およそ 10^-7 K の精度）
HEAT_RESIDUAL_TOL = 1.0e-6


def step_heat(geometry: WallGeometry, state_n: WallState, dt: float,
              t_outdoor: float, t_indoor: float) -> tuple[WallState, int]:
    """熱だけを 1 ステップ進める（水分化学ポテンシャルは変えない）。

    次の時刻の温度は、熱の収支の残差が 0 になるように、ニュートン法で求める。最初の仮の値は前の時刻の温度。
    この段階では水分化学ポテンシャルを変えないので、温度が変わると相対湿度は変わる（段階 5 で熱と水分を一緒に解く）。

    Args:
        geometry: 壁の形
        state_n: 前の時刻（ステップ n）の状態
        dt: 時間刻み, s
        t_outdoor: 次の時刻の外気温, K
        t_indoor: 次の時刻の室温, K

    Returns:
        次の時刻（ステップ n + 1）の状態、ニュートン法で修正した回数
    """

    # 次の時刻の温度の仮の値 t_is を受け取って、熱の収支の残差を返す関数（この 1 ステップ専用。ほかの値は覚えておく）
    def residual(t_is):
        return heat_residual_is(geometry, t_is, state_n.t_is, dt, t_outdoor, t_indoor)

    # 残差が 0 になる温度を、前の時刻の温度から探す
    t_is, m = newton_solve(residual, state_n.t_is, band=HEAT_BAND, tol=HEAT_RESIDUAL_TOL)

    # 水分化学ポテンシャルは、前の時刻のまま
    return WallState(t_is=t_is, mu_is=state_n.mu_is), m
