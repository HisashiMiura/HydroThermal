"""室内の気候：経過時間から、室内の境界条件を作る（段階 6）。

経過時間の起点は 1 月 1 日 0 時。1 年は 365 日（うるう年なし）で、2 年目以降も同じ周期で続く。
今の room.Room（ステップ番号で配列から取り出す）は、置き換えが終わったら消す。
"""

from dataclasses import dataclass

import numpy as np

from modules.boundary import IndoorBoundary

# 1 日, s
SECONDS_PER_DAY = 86400.0

# 1 年（365 日）, s
SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY


@dataclass(frozen=True, kw_only=True)
class CosineIndoor:
    """室温が 1 年周期の余弦で変わり、相対湿度は一定の室内。

    θ(time) = 平均 + 振幅 × cos(2π (time - time_peak) / 1 年)。
    いちばん暑い時刻 time_peak は、いちばん暑い日（通算日 peak_day）の 12 時。
    Fortran の SUBROUTINE ROOM は 1 日の中で一定（日ごとの段）で、その日の値が極大になる。ここでは滑らかに変え、日の真ん中を極大にする。
    """

    # 年平均の室温, deg.C
    theta_average: float

    # 室温の振幅, K
    theta_amplitude: float

    # 相対湿度, %（一定）
    rh: float

    # いちばん暑い日の通算日（1 月 1 日が 1）
    peak_day: int = 212

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 振幅が負ならエラー（負の振幅は、極大と極小が入れ替わるだけで紛らわしい）
        if self.theta_amplitude < 0.0:
            raise ValueError(f'室温の振幅 theta_amplitude は 0 以上にしてください（{self.theta_amplitude}）。')

        # 相対湿度が 0 より大きく 100 以下でなければエラー
        if not 0.0 < self.rh <= 100.0:
            raise ValueError(f'相対湿度 rh は 0 より大きく 100 以下にしてください（{self.rh}）。')

        # いちばん暑い日が 1〜365 の整数でなければエラー
        if not isinstance(self.peak_day, int) or not 1 <= self.peak_day <= 365:
            raise ValueError(f'いちばん暑い日 peak_day は 1〜365 の整数にしてください（{self.peak_day}）。')

    @property
    def time_peak(self) -> float:
        """いちばん暑い時刻（1 月 1 日 0 時からの経過時間）, s。通算日 peak_day の 12 時。"""
        return (self.peak_day - 1 + 0.5) * SECONDS_PER_DAY

    def theta(self, time: float) -> float:
        """1 月 1 日 0 時からの経過時間 time（s）の室温, deg.C。"""
        return self.theta_average + self.theta_amplitude * np.cos(2.0 * np.pi * (time - self.time_peak) / SECONDS_PER_YEAR)

    def at(self, time: float) -> IndoorBoundary:
        """1 月 1 日 0 時からの経過時間 time（s）の室内の境界条件。"""
        return IndoorBoundary.from_theta_rh(theta=self.theta(time), rh=self.rh)
