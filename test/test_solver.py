import numpy as np
import pytest

from modules.balance import heat_capacity_is, heat_flow_ks, liquid_flow_ks, vapour_flow_ks, water_amount_is
from modules.boundary import IndoorBoundary, OutdoorBoundary
from modules.solver import HEAT_RESIDUAL_TOL, MOISTURE_RESIDUAL_TOL, step
from modules.state import State
from modules.thermo_dynamics import ATP, RW, get_wp
from modules.wall_builder import build_wall
from modules.wall_geometry import WallGeometry
from modules.wall_input import WallInput
from modules.wall_state import WallState

_SURFACE = {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2}


def _outdoor(theta: float, rh: float) -> OutdoorBoundary:
    """外気温 theta（deg.C）・相対湿度 rh（%）の外気の境界条件。"""
    return OutdoorBoundary.from_theta_rh(theta=theta, rh=rh)


def _indoor(theta: float, rh: float) -> IndoorBoundary:
    """室温 theta（deg.C）・相対湿度 rh（%）の室内の境界条件。"""
    return IndoorBoundary.from_theta_rh(theta=theta, rh=rh)


def _one_layer(name: str, thickness: float, n_div: int, theta: float, rh: float) -> tuple[WallGeometry, WallState]:
    """1 層の壁（外表面 22.4・2.0e-11、内表面 9.2・2.6e-10）。初期は theta（deg.C）・rh（%）で一様。"""
    return build_wall(WallInput.from_dict({
        'surface': _SURFACE,
        'layers': [{'source': 'whamcavity', 'name': name, 'thickness': thickness, 'n_div': n_div,
                    'initial_temperature': theta, 'initial_rh': rh}],
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


def _moisture_flow_ks(g, state, outdoor, indoor):
    """つながりごとの水分の流れ（水蒸気 + 液水）, kg/(m2 s), [k]。"""
    return (vapour_flow_ks(g, state.t_is, state.mu_is, outdoor, indoor)
            + liquid_flow_ks(g, state.t_is, state.mu_is, outdoor, indoor))


def _total_heat_flow_ks(g, state, outdoor, indoor):
    """つながりごとの熱の流れ（熱伝導 + 水蒸気が運ぶ潜熱）, W/m2, [k]。"""
    return (heat_flow_ks(g, state.t_is, outdoor, indoor)
            + RW * vapour_flow_ks(g, state.t_is, state.mu_is, outdoor, indoor))


class TestStep:

    def test_uniform(self):
        # 外気・室内・壁がすべて 20 deg.C・50% なら、1 ステップ進めても変わらない
        g, state_n = _one_layer('構造用合板1', 0.009, 6, 20.0, 50.0)
        state, _ = step(g, state_n, dt=180.0, outdoor=_outdoor(20.0, 50.0), indoor=_indoor(20.0, 50.0))
        np.testing.assert_allclose(state.theta_is, 20.0)
        np.testing.assert_allclose(state.rh_is, 50.0)

    def test_iterations(self):
        # 非線形だが、数回（5 回以下）の修正で収束する
        g, state_n = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        _, m = step(g, state_n, dt=180.0, outdoor=_outdoor(0.0, 80.0), indoor=_indoor(20.0, 50.0))
        assert 1 <= m <= 5

    def test_conservation(self):
        # 1 ステップで壁にたまった水分 = (外気から入った水分 - 室内へ出た水分) × Δt。
        # 熱も同じ（潜熱を含む。たまった熱は、次の時刻の熱容量 × 温度の変化）。
        # ずれてよいのは、ニュートン法の許容値の分（質点の数 × 許容値 × Δt）まで
        g, state_n = _one_layer('構造用合板1', 0.009, 6, 10.0, 50.0)
        dt = 180.0
        outdoor, indoor = _outdoor(0.0, 80.0), _indoor(20.0, 50.0)
        state, _ = step(g, state_n, dt=dt, outdoor=outdoor, indoor=indoor)

        w_stored = (water_amount_is(g, state.t_is, state.mu_is) - water_amount_is(g, state_n.t_is, state_n.mu_is)).sum()
        j_ks = _moisture_flow_ks(g, state, outdoor, indoor)
        assert w_stored == pytest.approx((j_ks[0] - j_ks[-1]) * dt, rel=0.0, abs=len(g.nodes) * MOISTURE_RESIDUAL_TOL * dt)

        h_stored = (heat_capacity_is(g, state.t_is, state.mu_is) * (state.t_is - state_n.t_is)).sum()
        q_ks = _total_heat_flow_ks(g, state, outdoor, indoor)
        assert h_stored == pytest.approx((q_ks[0] - q_ks[-1]) * dt, rel=0.0, abs=len(g.nodes) * HEAT_RESIDUAL_TOL * dt)

    def test_absorption(self):
        # 構造用合板1 の 1 層、20 deg.C 一定、初期 50%、外気・室内とも 70%。
        # 1 年（Δt = 1 日）進めると、どの質点も 70% になり、水分量の増えた分が、吸った水分の合計と一致する。
        # 平衡の近くでは、1 ステップの変化が許容値より小さくなって止まるので、70% との差は 1e-3% まで許す
        g, state_0 = _one_layer('構造用合板1', 0.009, 6, 20.0, 50.0)
        outdoor, indoor = _outdoor(20.0, 70.0), _indoor(20.0, 70.0)
        dt, n_steps = 86400.0, 365
        state, absorbed = state_0, 0.0
        for _ in range(n_steps):
            state, _ = step(g, state, dt=dt, outdoor=outdoor, indoor=indoor)
            j_ks = _moisture_flow_ks(g, state, outdoor, indoor)
            absorbed += (j_ks[0] - j_ks[-1]) * dt
        np.testing.assert_allclose(state.rh_is, 70.0, atol=1e-3)
        np.testing.assert_allclose(state.theta_is, 20.0, atol=1e-6)
        w_increase = (water_amount_is(g, state.t_is, state.mu_is) - water_amount_is(g, state_0.t_is, state_0.mu_is)).sum()
        assert w_increase > 0.0
        assert w_increase == pytest.approx(absorbed, rel=0.0, abs=n_steps * len(g.nodes) * MOISTURE_RESIDUAL_TOL * dt)

    def test_steady_vapour(self):
        # 湿気伝導率が一定の構造用合板2、20 deg.C 一定、外気 30%・室内 70%。
        # 1 年（Δt = 1 日）進めると定常になり、どのつながりの水蒸気の流れも (p_v,外 - p_v,内) / 透湿抵抗の合計
        g, state = _one_layer('構造用合板2', 0.012, 5, 20.0, 50.0)
        outdoor, indoor = _outdoor(20.0, 30.0), _indoor(20.0, 70.0)
        for _ in range(365):
            state, _ = step(g, state, dt=86400.0, outdoor=outdoor, indoor=indoor)
        state_any = State.init(t=20.0 + ATP, rh=50.0)
        r_m_total = sum(link.r_m(state_any, state_any) for link in g.links)
        j_v_ks = vapour_flow_ks(g, state.t_is, state.mu_is, outdoor, indoor)
        np.testing.assert_allclose(j_v_ks, (outdoor.state.p_v - indoor.state.p_v) / r_m_total, rtol=1e-4)

    def test_steady_main_wall(self):
        # 今の壁 7 層、外気 0 deg.C・80%、室内 20 deg.C・50%（換気・日射なし）。
        # 1 年（Δt = 1 日）進めると、熱は定常になり、どのつながりの熱の流れ（潜熱を含む）も同じ値になる。
        # 水分は両側の湿気の抵抗が大きく、1 年では定常にならないので、結露していない（100% 未満）ことだけ確かめる
        g, state = _main_wall()
        outdoor, indoor = _outdoor(0.0, 80.0), _indoor(20.0, 50.0)
        for _ in range(365):
            state, _ = step(g, state, dt=86400.0, outdoor=outdoor, indoor=indoor)
        assert state.rh_is.max() < 100.0
        q_ks = _total_heat_flow_ks(g, state, outdoor, indoor)
        np.testing.assert_allclose(q_ks, q_ks.mean(), rtol=1e-5)
