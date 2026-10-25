"""境界条件：ある時刻の外気と室内の条件（docs/governing_equations.md 5.3 節）。

外気と室内は、持つ値が違うので別のクラスにする（外気は日射・夜間放射を持つ。段階 7 で雨・風を足す）。
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


@dataclass(frozen=True, kw_only=True)
class SolarRadiation:
    """ある時刻の太陽の位置と、日射・夜間放射（壁の向きによらない値）。

    壁面に当たる量は、壁の外表面（wall_geometry.Surface.solar_heat_gain）が向きと傾斜から求める。
    """

    # 太陽高度の正弦・余弦, -
    sin_h: float
    cos_h: float

    # 太陽方位角（南が 0、西回りが正）の正弦・余弦, -
    sin_a: float
    cos_a: float

    # 法線面直達日射量, W/m2
    i_dn: float

    # 水平面天空日射量, W/m2
    i_sky: float

    # 夜間放射量（水平面）, W/m2
    r_n: float

    def __post_init__(self):
        """作るときに値を確かめる。"""

        # 日射量が負ならエラー
        if self.i_dn < 0.0 or self.i_sky < 0.0:
            raise ValueError(f'日射量 i_dn・i_sky は 0 以上にしてください（{self.i_dn}, {self.i_sky}）。')


# 日射も夜間放射もない（太陽は地平線の上、真南にあるとしておく。日射が 0 なので位置は答えに効かない）
NO_SUN = SolarRadiation(sin_h=0.0, cos_h=1.0, sin_a=0.0, cos_a=1.0, i_dn=0.0, i_sky=0.0, r_n=0.0)


def _check_state(state: State, where: str):
    """状態が State でなければエラーにする。"""

    if not isinstance(state, State):
        raise ValueError(f'{where}の state は State にしてください（{type(state).__name__}）。')


@dataclass(frozen=True, kw_only=True)
class OutdoorBoundary:
    """ある時刻の外気の境界条件。

    雨・風速・風向は、段階 7 で足す。
    """

    # 外気の状態（温度・水分化学ポテンシャル。温度 state.t、相対湿度 state.rh、水蒸気圧 state.p_v を取り出せる）
    state: State

    # 太陽の位置と、日射・夜間放射（既定は、日射も夜間放射もない）
    solar: SolarRadiation = NO_SUN

    def __post_init__(self):
        """作るときに値を確かめる。"""
        _check_state(self.state, where='外気')

        # 日射が SolarRadiation でなければエラー
        if not isinstance(self.solar, SolarRadiation):
            raise ValueError(f'外気の solar は SolarRadiation にしてください（{type(self.solar).__name__}）。')

    @classmethod
    def from_theta_rh(cls, theta: float, rh: float, solar: SolarRadiation = NO_SUN) -> Self:
        """外気温（deg.C）と相対湿度（%）、日射から作る。"""
        return cls(state=_state_from_theta_rh(theta, rh), solar=solar)


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
