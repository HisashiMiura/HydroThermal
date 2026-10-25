import numpy as np
import pytest

from modules.boundary import Boundaries
from modules.simulation import simulate
from modules.solver import step
from test.test_solver import _indoor, _one_layer, _outdoor


def _constant(theta_o: float, rh_o: float, theta_i: float, rh_i: float):
    """時刻によらず一定の境界条件の関数。"""
    b = Boundaries(outdoor=_outdoor(theta_o, rh_o), indoor=_indoor(theta_i, rh_i))
    return lambda time: b


class TestSimulate:

    def test_same_as_step(self):
        # step を自分で 10 回繰り返したのと、同じ答えになる
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        boundaries_at = _constant(0.0, 80.0, 20.0, 50.0)
        result = simulate(g, state_0, dt=180.0, n_steps=10, boundaries_at=boundaries_at)

        state = state_0
        for _ in range(10):
            b = boundaries_at(0.0)
            state, _ = step(g, state, 180.0, b.outdoor, b.indoor)
        np.testing.assert_array_equal(result.state_last.t_is, state.t_is)
        np.testing.assert_array_equal(result.state_last.mu_is, state.mu_is)

    def test_record(self):
        # 毎ステップ記録すると、記録は最初の状態 ＋ 10 個。最初の記録は最初の状態、最後の記録は最後の状態
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        result = simulate(g, state_0, dt=180.0, n_steps=10, boundaries_at=_constant(0.0, 80.0, 20.0, 50.0))
        assert result.t_nis.shape == result.mu_nis.shape == (11, len(g.nodes))
        np.testing.assert_allclose(result.time_ns, 180.0 * np.arange(11))
        np.testing.assert_array_equal(result.t_nis[0], state_0.t_is)
        np.testing.assert_array_equal(result.state(10).t_is, result.state_last.t_is)
        assert len(result.iterations_ns) == 10
        assert np.all(result.iterations_ns >= 1)

    def test_record_every(self):
        # 3 ステップごとに記録すると、10 ステップでは 0・3・6・9 ステップ目の 4 個。最後の状態は記録と別に持つ
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        boundaries_at = _constant(0.0, 80.0, 20.0, 50.0)
        every_1 = simulate(g, state_0, dt=180.0, n_steps=10, boundaries_at=boundaries_at)
        every_3 = simulate(g, state_0, dt=180.0, n_steps=10, boundaries_at=boundaries_at, record_every=3)
        np.testing.assert_allclose(every_3.time_ns, [0.0, 540.0, 1080.0, 1620.0])
        np.testing.assert_array_equal(every_3.t_nis, every_1.t_nis[[0, 3, 6, 9]])
        np.testing.assert_array_equal(every_3.state_last.t_is, every_1.state_last.t_is)

    def test_time_of_boundaries(self):
        # 境界条件は、各ステップの終わりの時刻（Δt, 2Δt, …）で問い合わせる（後退差分）
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        constant = _constant(10.0, 50.0, 10.0, 50.0)
        asked = []

        def boundaries_at(time):
            asked.append(time)
            return constant(time)

        simulate(g, state_0, dt=180.0, n_steps=4, boundaries_at=boundaries_at)
        assert asked == [180.0, 360.0, 540.0, 720.0]

    def test_steady(self):
        # 一定の境界条件で長く進めると、段階 5 と同じく、吸湿して 70% の平衡になる
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 20.0, 50.0)
        result = simulate(g, state_0, dt=86400.0, n_steps=365, boundaries_at=_constant(20.0, 70.0, 20.0, 70.0),
                          record_every=30)
        np.testing.assert_allclose(result.state_last.rh_is, 70.0, atol=1e-4)

    def test_zero_steps(self):
        # 0 ステップなら、最初の状態だけ
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        result = simulate(g, state_0, dt=180.0, n_steps=0, boundaries_at=_constant(0.0, 80.0, 20.0, 50.0))
        assert result.t_nis.shape == (1, len(g.nodes))
        assert result.state_last is state_0

    @pytest.mark.parametrize('kwargs, match', [
        ({'dt': 0.0}, 'dt'),
        ({'n_steps': -1}, 'n_steps'),
        ({'n_steps': 1.5}, 'n_steps'),
        ({'record_every': 0}, 'record_every'),
    ])
    def test_invalid(self, kwargs, match):
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        args = {'dt': 180.0, 'n_steps': 1, 'boundaries_at': _constant(0.0, 80.0, 20.0, 50.0)} | kwargs
        with pytest.raises(ValueError, match=match):
            simulate(g, state_0, **args)
