"""境界条件：ある時刻の外気と室内の条件（docs/governing_equations.md 5.3 節）。

外気と室内は、持つ値が違うので別のクラスにする（外気には、段階 6・7 で日射・夜間放射・雨・風を足す）。
壁の形の外気（Outdoor）・室内（Indoor）に対応する。
"""

from dataclasses import dataclass
from typing import Self

from modules.state import State
from modules.thermo_dynamics import ATP


def _state_from_theta_rh(theta: float, rh: float) -> State:
    """温度と相対湿度から、1 点の状態を作る（外気・室内で共通）。

    Args:
        theta: 温度, deg.C
        rh: 相対湿度, %（0 より大きく 100 以下）
    """

    # 相対湿度が 0 より大きく 100 以下でなければエラー
    # （0 では水分化学ポテンシャルが −∞ になる。100 は飽和で μ = 0。外気は雨や霧で飽和することがあるので受け付ける）
    if not 0.0 < rh <= 100.0:
        raise ValueError(f'相対湿度 rh は 0 より大きく 100 以下にしてください（{rh}）。')

    return State.init(t=theta + ATP, rh=rh)


def _check_state(state: State, where: str):
    """状態が State でなければエラーにする。"""

    if not isinstance(state, State):
        raise ValueError(f'{where}の state は State にしてください（{type(state).__name__}）。')


@dataclass(frozen=True, kw_only=True)
class OutdoorBoundary:
    """ある時刻の外気の境界条件。

    日射・夜間放射・雨・風速・風向は、段階 6・7 で足す。
    """

    # 外気の状態（温度・水分化学ポテンシャル。温度 state.t、相対湿度 state.rh、水蒸気圧 state.p_v を取り出せる）
    state: State

    def __post_init__(self):
        """作るときに値を確かめる。"""
        _check_state(self.state, where='外気')

    @classmethod
    def from_theta_rh(cls, theta: float, rh: float) -> Self:
        """外気温（deg.C）と相対湿度（%）から作る。"""
        return cls(state=_state_from_theta_rh(theta, rh))


@dataclass(frozen=True, kw_only=True)
class IndoorBoundary:
    """ある時刻の室内の境界条件。"""

    # 室内の状態（温度・水分化学ポテンシャル）
    state: State

    def __post_init__(self):
        """作るときに値を確かめる。"""
        _check_state(self.state, where='室内')

    @classmethod
    def from_theta_rh(cls, theta: float, rh: float) -> Self:
        """室温（deg.C）と相対湿度（%）から作る。"""
        return cls(state=_state_from_theta_rh(theta, rh))


@dataclass(frozen=True, kw_only=True)
class Boundaries:
    """ある時刻の外気と室内の境界条件の組（1 ステップを進めるのに使う）。"""

    # 外気の境界条件
    outdoor: OutdoorBoundary

    # 室内の境界条件
    indoor: IndoorBoundary

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 外気・室内の境界条件のクラスでなければエラー（取り違えを防ぐ）
        if not isinstance(self.outdoor, OutdoorBoundary):
            raise ValueError(f'outdoor は OutdoorBoundary にしてください（{type(self.outdoor).__name__}）。')
        if not isinstance(self.indoor, IndoorBoundary):
            raise ValueError(f'indoor は IndoorBoundary にしてください（{type(self.indoor).__name__}）。')
