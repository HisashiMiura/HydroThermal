import dataclasses

import numpy as np
import pytest

from modules.thermo_dynamics import ATP, get_wp
from modules.wall_state import WallState


def _state() -> WallState:
    """質点 3 個の状態（10・15・20 deg.C、相対湿度 50・80・95%）。"""
    t_is = np.array([10.0, 15.0, 20.0]) + ATP
    mu_is = np.array([get_wp(rh=rh_i, t=t_i) for rh_i, t_i in zip((50.0, 80.0, 95.0), t_is)])
    return WallState(t_is=t_is, mu_is=mu_is)


class TestWallState:

    def test_values(self):
        state = _state()
        assert len(state) == 3
        np.testing.assert_allclose(state.t_is, np.array([10.0, 15.0, 20.0]) + ATP)

    def test_read_only(self):
        # 配列の中身も、項目の付け替えも、書き換えられない
        state = _state()
        with pytest.raises(ValueError):
            state.t_is[0] = 300.0
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.t_is = np.zeros(3)

    def test_copied(self):
        # 作ったあとに、渡したもとの配列を書き換えても、中身は変わらない
        t_is = np.array([283.15, 288.15])
        mu_is = np.array([-1.0e7, -2.0e7])
        state = WallState(t_is=t_is, mu_is=mu_is)
        t_is[0] = 0.0
        assert state.t_is[0] == 283.15

    def test_different_length(self):
        with pytest.raises(ValueError, match='長さ'):
            WallState(t_is=np.array([283.15, 288.15]), mu_is=np.array([-1.0e7]))

    def test_not_1d(self):
        with pytest.raises(ValueError, match='1 次元'):
            WallState(t_is=np.zeros((2, 2)), mu_is=np.zeros((2, 2)))

    def test_theta(self):
        np.testing.assert_allclose(_state().theta_is, [10.0, 15.0, 20.0])

    def test_rh(self):
        # 相対湿度から水分化学ポテンシャルを作ると、rh で元に戻る
        np.testing.assert_allclose(_state().rh_is, [50.0, 80.0, 95.0])

    def test_state(self):
        # 質点 i の 1 点の状態
        state = _state()
        state_i = state.state(1)
        assert (state_i.t, state_i.mu) == (state.t_is[1], state.mu_is[1])
        assert state_i.rh == pytest.approx(80.0)
