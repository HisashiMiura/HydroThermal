import numpy as np
import pytest

from modules.balance import heat_flow_ks
from modules.solver import step_heat
from modules.thermo_dynamics import ATP, get_wp
from modules.wall_builder import build_wall
from modules.wall_geometry import WallGeometry
from modules.wall_input import WallInput
from modules.wall_state import WallState

_SURFACE = {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2}


def _one_layer() -> tuple[WallGeometry, WallState]:
    """1 層の壁：構造用合板1 9 mm（分割数 6）、外表面 22.4、内表面 9.2。初期は 10 deg.C・50%。"""
    return build_wall(WallInput.from_dict({
        'surface': _SURFACE,
        'layers': [{'source': 'whamcavity', 'name': '構造用合板1', 'thickness': 0.009, 'n_div': 6,
                    'initial_temperature': 10.0, 'initial_rh': 50.0}],
        'interfaces': [{'cond_h': 22.4, 'cond_m': 2.0e-11}, {'cond_h': 9.2, 'cond_m': 2.6e-10}],
        'len_vertical': 1.0, 'len_horizontal': 1.0, 'height': 1.0,
    }))


def _main_wall() -> tuple[WallGeometry, WallState]:
    """今の main.py・Fortran の入力の壁 7 層（通気層を含む。換気はまだ扱わない）。"""

    def m(name, thickness, n_div, temperature, rh):
        return {'source': 'whamcavity', 'name': name, 'thickness': thickness, 'n_div': n_div,
                'initial_temperature': temperature, 'initial_rh': rh}

    return build_wall(WallInput.from_dict({
        'surface': _SURFACE,
        'layers': [
            m('サイディング', 0.016, 5, 15.0, 50.0),
            {'air_layer': True, 'thickness': 0.025, 'alpha': 0.085, 'initial_temperature': 15.0, 'initial_rh': 50.0},
            m('石膏ボード', 0.042, 5, 10.0, 50.0),
            m('構造用合板1', 0.009, 6, 10.0, 80.0),
            m('グラスウール1', 0.1, 5, 10.0, 50.0),
            m('構造用合板1', 0.012, 6, 10.0, 80.0),
            m('石膏ボード', 0.042, 5, 10.0, 50.0),
        ],
        'interfaces': [{'cond_h': h, 'cond_m': w} for h, w in (
            (22.4, 2.0e-11), (9.2, 3.43e-8), (9.2, 3.43e-8), (50.0, 7.75e-7),
            (50.0, 7.75e-7), (50.0, 2.0e-11), (50.0, 7.75e-7), (9.2, 2.6e-10),
        )],
        'len_vertical': 7.0, 'len_horizontal': 0.42, 'height': 7.0,
    }))


def _uniform_state(g: WallGeometry, theta: float, rh: float) -> WallState:
    """全部の質点が同じ温度・相対湿度の状態。"""
    t = theta + ATP
    return WallState(t_is=np.full(len(g.nodes), t), mu_is=np.full(len(g.nodes), get_wp(rh=rh, t=t)))


def _r_h_total(g: WallGeometry) -> float:
    """熱貫流抵抗（全部のつながりの熱抵抗の和）, (m2 K)/W。"""
    return sum(link.r_h for link in g.links)


class TestStepHeat:

    def test_uniform(self):
        # 外気・室内・壁がすべて 20 deg.C なら、1 ステップ進めても 20 deg.C のまま
        g, _ = _one_layer()
        state_n = _uniform_state(g, 20.0, 50.0)
        state, _ = step_heat(g, state_n, dt=180.0, t_outdoor=20.0 + ATP, t_indoor=20.0 + ATP)
        np.testing.assert_allclose(state.theta_is, 20.0)

    def test_iterations(self):
        # 熱だけ（線形）なので、1〜2 回の修正で収束する
        g, state_n = _one_layer()
        _, m = step_heat(g, state_n, dt=180.0, t_outdoor=0.0 + ATP, t_indoor=20.0 + ATP)
        assert 1 <= m <= 2

    def test_conservation(self):
        # 1 ステップで壁にたまった熱 = (外気から入った熱 - 室内へ出た熱) × Δt（次の時刻の温度で計算）
        g, state_n = _one_layer()
        dt = 180.0
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        state, _ = step_heat(g, state_n, dt=dt, t_outdoor=t_outdoor, t_indoor=t_indoor)
        c_is = np.array([node.heat_capacity for node in g.nodes])
        stored = (c_is * (state.t_is - state_n.t_is)).sum()
        q_ks = heat_flow_ks(g, state.t_is, t_outdoor=t_outdoor, t_indoor=t_indoor)
        assert stored == pytest.approx((q_ks[0] - q_ks[-1]) * dt, rel=1e-6)

    def test_steady_one_layer(self):
        # 外気 0 deg.C・室内 20 deg.C で十分長く進めると、手計算の直線の温度分布（熱抵抗に比例）になる
        g, state = _one_layer()
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        for _ in range(200):
            state, _ = step_heat(g, state, dt=600.0, t_outdoor=t_outdoor, t_indoor=t_indoor)
        r_h_ks = np.array([link.r_h for link in g.links])
        q = (t_outdoor - t_indoor) / r_h_ks.sum()
        np.testing.assert_allclose(state.t_is, t_outdoor - q * np.cumsum(r_h_ks)[:-1], atol=1e-6)

    def test_steady_main_wall(self):
        # 今の壁で十分長く進めると、どのつながりの熱の流れも 温度差 / 熱貫流抵抗 になる
        g, state = _main_wall()
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        for _ in range(1000):
            state, _ = step_heat(g, state, dt=3600.0, t_outdoor=t_outdoor, t_indoor=t_indoor)
        q_ks = heat_flow_ks(g, state.t_is, t_outdoor=t_outdoor, t_indoor=t_indoor)
        np.testing.assert_allclose(q_ks, (t_outdoor - t_indoor) / _r_h_total(g), rtol=1e-6)

    def test_mu_unchanged(self):
        # 水分化学ポテンシャルは、前の時刻のまま
        g, state_n = _one_layer()
        state, _ = step_heat(g, state_n, dt=180.0, t_outdoor=0.0 + ATP, t_indoor=20.0 + ATP)
        np.testing.assert_array_equal(state.mu_is, state_n.mu_is)
