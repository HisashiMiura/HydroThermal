"""時間を進めるループ（段階 6、設計の文書 3 章）。

境界条件は、経過時間（秒）を渡すとその時刻の値を返す関数で受け取る（Δt と切り離すため）。
1 ステップを進める部分は solver.step。
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from modules.boundary import Boundaries
from modules.solver import step
from modules.wall_geometry import WallGeometry
from modules.wall_state import WallState

# 境界条件の関数：計算を始めてからの経過時間, s → その時刻の外気と室内の境界条件
BoundariesAt = Callable[[float], Boundaries]


@dataclass(frozen=True, eq=False)
class SimulationResult:
    """時間を進めた結果。

    記録は最初の状態（経過時間 0）と、record_every ステップごとの状態（添え字 n は記録の番号）。
    """

    # 記録した時刻（計算を始めてからの経過時間）, s, [n]
    time_ns: np.ndarray

    # 記録した時刻の各質点の温度, K, [n, i]
    t_nis: np.ndarray

    # 記録した時刻の各質点の水分化学ポテンシャル, J/kg, [n, i]
    mu_nis: np.ndarray

    # 各ステップのニュートン法の修正の回数, [ステップ]
    iterations_ns: np.ndarray

    # 最後のステップのあとの状態（記録の間隔によらず、続きの計算に使える）
    state_last: WallState

    def state(self, n: int) -> WallState:
        """記録 n の壁の状態。"""
        return WallState(t_is=self.t_nis[n], mu_is=self.mu_nis[n])


def simulate(
        geometry: WallGeometry,
        state_0: WallState,
        dt: float,
        n_steps: int,
        boundaries_at: BoundariesAt,
        record_every: int = 1
    ) -> SimulationResult:
    """境界条件に沿って、n_steps ステップ進める。

    ステップ n（0 〜 n_steps - 1）は、時刻 n Δt の状態から、ステップの終わりの時刻 (n + 1) Δt の境界条件
    boundaries_at((n + 1) Δt) を使って（後退差分）、時刻 (n + 1) Δt の状態を求める。

    Args:
        geometry: 壁の形
        state_0: 最初（経過時間 0）の状態
        dt: 時間刻み, s
        n_steps: 進めるステップの数
        boundaries_at: 経過時間, s → その時刻の境界条件
        record_every: 何ステップごとに記録するか（1 なら毎ステップ）

    Returns:
        時間を進めた結果

    Raises:
        Condensation: 結露して、相対湿度 100% 以下では収支が合わないとき（solver.step）
        NewtonNotConverged: それ以外の理由で収束しなかったとき（solver.step）
    """

    # 時間刻みが正でなければエラー
    if not dt > 0.0:
        raise ValueError(f'時間刻み dt は正にしてください（{dt}）。')

    # ステップの数が 0 以上の整数でなければエラー（0 なら最初の状態だけを返す）
    if not isinstance(n_steps, int) or n_steps < 0:
        raise ValueError(f'ステップの数 n_steps は 0 以上の整数にしてください（{n_steps}）。')

    # 記録の間隔が 1 以上の整数でなければエラー
    if not isinstance(record_every, int) or record_every < 1:
        raise ValueError(f'記録の間隔 record_every は 1 以上の整数にしてください（{record_every}）。')

    # 記録の数（最初の状態 ＋ record_every ステップごと）
    n_records = 1 + n_steps // record_every

    time_ns = np.empty(n_records)
    t_nis = np.empty((n_records, len(state_0)))
    mu_nis = np.empty((n_records, len(state_0)))
    iterations_ns = np.empty(n_steps, dtype=int)

    # 最初の状態を記録する
    time_ns[0], t_nis[0], mu_nis[0] = 0.0, state_0.t_is, state_0.mu_is

    state = state_0

    for n in range(n_steps):

        # ステップの終わりの時刻, s
        time_end = (n + 1) * dt

        # ステップの終わりの時刻の境界条件で、1 ステップ進める
        b = boundaries_at(time_end)
        state, iterations_ns[n] = step(geometry, state, dt, b.outdoor, b.indoor)

        # record_every ステップごとに記録する
        if (n + 1) % record_every == 0:
            r = (n + 1) // record_every
            time_ns[r], t_nis[r], mu_nis[r] = time_end, state.t_is, state.mu_is

    return SimulationResult(
        time_ns=time_ns,
        t_nis=t_nis,
        mu_nis=mu_nis,
        iterations_ns=iterations_ns,
        state_last=state,
    )
