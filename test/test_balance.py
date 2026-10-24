import numpy as np
import pytest

from modules.balance import heat_capacity_is, heat_flow_ks, heat_residual_is, liquid_flow_ks, vapour_flow_ks, water_amount_is
from modules.boundary import IndoorBoundary, OutdoorBoundary
from modules.state import State
from modules.thermo_dynamics import ATP, get_wp
from modules.wall_geometry import WallGeometry
from modules.wall_input import WallInput


def _outdoor(t: float) -> OutdoorBoundary:
    """外気温 t（K）の外気の境界条件（熱だけの計算なので、相対湿度は 50% とする）。"""
    return OutdoorBoundary(state=State.init(t=t, rh=50.0))


def _indoor(t: float) -> IndoorBoundary:
    """室温 t（K）の室内の境界条件（相対湿度は 50%）。"""
    return IndoorBoundary(state=State.init(t=t, rh=50.0))


def _one_layer_geometry() -> WallGeometry:
    """1 層の壁：構造用合板1 9 mm（分割数 6）、外表面 22.4、内表面 9.2。"""
    return WallGeometry.from_input(WallInput.from_dict({
        'surface': {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2},
        'layers': [{'source': 'whamcavity', 'name': '構造用合板1', 'thickness': 0.009, 'n_div': 6,
                    'initial_temperature': 10.0, 'initial_rh': 50.0}],
        'interfaces': [{'cond_h': 22.4, 'cond_m': 2.0e-11}, {'cond_h': 9.2, 'cond_m': 2.6e-10}],
        'len_vertical': 1.0,
        'len_horizontal': 1.0,
        'height': 1.0,
    }))


class TestHeatFlow:

    def test_uniform(self):
        # 外気・室内・全部の質点が 20 deg.C なら、熱は流れない
        g = _one_layer_geometry()
        t = 20.0 + ATP
        q_ks = heat_flow_ks(g, np.full(len(g.nodes), t), outdoor=_outdoor(t), indoor=_indoor(t))
        np.testing.assert_allclose(q_ks, 0.0)

    def test_steady(self):
        # 外気 0 deg.C・室内 20 deg.C の定常の温度分布（抵抗に比例した直線）を入れると、
        # どのつながりの熱の流れも同じで、(0 - 20) / 熱貫流抵抗 に等しい
        g = _one_layer_geometry()
        r_h_ks = np.array([link.r_h for link in g.links])
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        q = (t_outdoor - t_indoor) / r_h_ks.sum()

        # 質点 i の温度 = 外気温 - q × (つながり 0〜i の熱抵抗の和)
        t_is = t_outdoor - q * np.cumsum(r_h_ks)[:-1]

        q_ks = heat_flow_ks(g, t_is, outdoor=_outdoor(t_outdoor), indoor=_indoor(t_indoor))
        np.testing.assert_allclose(q_ks, q)

    def test_direction(self):
        # 外気のほうが温かければ、外気側から室内側へ（正の向きに）流れる
        g = _one_layer_geometry()
        t = 20.0 + ATP
        q_ks = heat_flow_ks(g, np.full(len(g.nodes), t), outdoor=_outdoor(t + 10.0), indoor=_indoor(t))
        assert q_ks[0] > 0.0
        assert q_ks[-1] == pytest.approx(0.0)

    def test_number(self):
        # 流れの数は、つながりの数（質点の数 + 1）
        g = _one_layer_geometry()
        q_ks = heat_flow_ks(g, np.full(len(g.nodes), 293.15), outdoor=_outdoor(293.15), indoor=_indoor(293.15))
        assert len(q_ks) == len(g.links) == len(g.nodes) + 1


def _steady_t_is(g: WallGeometry, t_outdoor: float, t_indoor: float) -> np.ndarray:
    """定常の温度分布（熱抵抗に比例した直線）, K, [i]。"""
    r_h_ks = np.array([link.r_h for link in g.links])
    q = (t_outdoor - t_indoor) / r_h_ks.sum()
    return t_outdoor - q * np.cumsum(r_h_ks)[:-1]


class TestHeatResidual:

    def test_steady(self):
        # 定常の温度分布を前の時刻と次の時刻の両方に入れると、残差は 0（たまる量も、正味の熱も 0）
        g = _one_layer_geometry()
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        t_is = _steady_t_is(g, t_outdoor, t_indoor)
        res_is = heat_residual_is(g, t_is, t_is, dt=180.0, outdoor=_outdoor(t_outdoor), indoor=_indoor(t_indoor))
        np.testing.assert_allclose(res_is, 0.0, atol=1e-9)

    def test_uniform(self):
        # すべて 20 deg.C のままなら、残差は 0
        g = _one_layer_geometry()
        t = 20.0 + ATP
        t_is = np.full(len(g.nodes), t)
        res_is = heat_residual_is(g, t_is, t_is, dt=180.0, outdoor=_outdoor(t), indoor=_indoor(t))
        np.testing.assert_allclose(res_is, 0.0)

    def test_storage_only(self):
        # 次の時刻はすべて 21 deg.C、前の時刻は 20 deg.C：熱は流れず、残差 = C_i × 1 K / Δt
        g = _one_layer_geometry()
        dt = 180.0
        t_n_is = np.full(len(g.nodes), 20.0 + ATP)
        t_is = t_n_is + 1.0
        res_is = heat_residual_is(g, t_is, t_n_is, dt=dt, outdoor=_outdoor(21.0 + ATP), indoor=_indoor(21.0 + ATP))
        c_is = np.array([node.heat_capacity_dry for node in g.nodes])
        np.testing.assert_allclose(res_is, c_is * 1.0 / dt)

    def test_conservation(self):
        # 残差の合計 = たまる量の合計 -（外気から入る熱 q_0 - 室内へ出る熱 q_N）。中のつながりの熱は打ち消し合う
        g = _one_layer_geometry()
        dt = 180.0
        t_n_is = np.linspace(5.0, 15.0, len(g.nodes)) + ATP
        t_is = np.linspace(6.0, 18.0, len(g.nodes)) + ATP
        t_outdoor, t_indoor = 0.0 + ATP, 20.0 + ATP
        res_is = heat_residual_is(g, t_is, t_n_is, dt=dt, outdoor=_outdoor(t_outdoor), indoor=_indoor(t_indoor))
        c_is = np.array([node.heat_capacity_dry for node in g.nodes])
        q_ks = heat_flow_ks(g, t_is, outdoor=_outdoor(t_outdoor), indoor=_indoor(t_indoor))
        storage = (c_is * (t_is - t_n_is) / dt).sum()
        assert res_is.sum() == pytest.approx(storage - (q_ks[0] - q_ks[-1]))


def _plywood2_geometry() -> WallGeometry:
    """1 層の壁：構造用合板2 12 mm（分割数 5、湿気伝導率が一定）、外表面の湿気 2.0e-11、内表面 2.6e-10。"""
    return WallGeometry.from_input(WallInput.from_dict({
        'surface': {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2},
        'layers': [{'source': 'whamcavity', 'name': '構造用合板2', 'thickness': 0.012, 'n_div': 5,
                    'initial_temperature': 20.0, 'initial_rh': 50.0}],
        'interfaces': [{'cond_h': 22.4, 'cond_m': 2.0e-11}, {'cond_h': 9.2, 'cond_m': 2.6e-10}],
        'len_vertical': 1.0,
        'len_horizontal': 1.0,
        'height': 1.0,
    }))


def _uniform(g: WallGeometry, t: float, rh: float) -> tuple[np.ndarray, np.ndarray]:
    """全部の質点が同じ温度 t（K）・相対湿度 rh（%）の t_is・mu_is。"""
    n = len(g.nodes)
    return np.full(n, t), np.full(n, get_wp(rh=rh, t=t))


class TestVapourFlow:

    def test_uniform(self):
        # 外気・室内・質点がすべて 20 deg.C・50% なら、水蒸気は流れない
        g = _one_layer_geometry()
        t = 20.0 + ATP
        t_is, mu_is = _uniform(g, t, 50.0)
        j_v_ks = vapour_flow_ks(g, t_is, mu_is,
                                outdoor=OutdoorBoundary(state=State.init(t=t, rh=50.0)),
                                indoor=IndoorBoundary(state=State.init(t=t, rh=50.0)))
        np.testing.assert_allclose(j_v_ks, 0.0, atol=1e-20)

    def test_steady(self):
        # 湿気伝導率が一定の 1 層の壁、20 deg.C 一定、外気 30%・室内 70%。
        # 水蒸気圧を透湿抵抗に比例した直線の分布にすると、どのつながりの流れも (p_v,外 - p_v,内) / 透湿抵抗の合計
        g = _plywood2_geometry()
        t = 20.0 + ATP
        outdoor = OutdoorBoundary(state=State.init(t=t, rh=30.0))
        indoor = IndoorBoundary(state=State.init(t=t, rh=70.0))
        state_any = State.init(t=t, rh=50.0)
        r_m_ks = np.array([link.r_m(state_any, state_any) for link in g.links])
        j = (outdoor.state.p_v - indoor.state.p_v) / r_m_ks.sum()

        # 質点 i の水蒸気圧 = 外気の水蒸気圧 - j × (つながり 0〜i の透湿抵抗の和)。温度は一定なので、相対湿度から μ を作る
        p_v_is = outdoor.state.p_v - j * np.cumsum(r_m_ks)[:-1]
        t_is = np.full(len(g.nodes), t)
        mu_is = np.array([get_wp(rh=100.0 * p_v_i / outdoor.state.p_v_sat, t=t) for p_v_i in p_v_is])

        j_v_ks = vapour_flow_ks(g, t_is, mu_is, outdoor=outdoor, indoor=indoor)
        np.testing.assert_allclose(j_v_ks, j, rtol=1e-9)

    def test_temperature_difference_only(self):
        # 相対湿度はどこも 50%、外気 0 deg.C・室内 20 deg.C：温かい室内側の水蒸気圧が高いので、室内側から外気側へ（負の向きに）流れる
        g = _one_layer_geometry()
        t_out, t_in = 0.0 + ATP, 20.0 + ATP
        # 質点の温度は外気温と室温の間（2〜18 deg.C）にする（端の質点を外気温・室温と同じにすると、表面のつながりで差がなくなる）
        t_is = np.linspace(t_out + 2.0, t_in - 2.0, len(g.nodes))
        mu_is = np.array([get_wp(rh=50.0, t=t_i) for t_i in t_is])
        j_v_ks = vapour_flow_ks(g, t_is, mu_is,
                                outdoor=OutdoorBoundary(state=State.init(t=t_out, rh=50.0)),
                                indoor=IndoorBoundary(state=State.init(t=t_in, rh=50.0)))
        assert np.all(j_v_ks < 0.0)

    def test_formula(self):
        # 各つながりの流れ = (左の水蒸気圧 - 右の水蒸気圧) / link.r_m(左, 右)
        g = _one_layer_geometry()
        n = len(g.nodes)
        t_is = np.linspace(5.0, 15.0, n) + ATP
        mu_is = np.array([get_wp(rh=rh, t=t_i) for rh, t_i in zip(np.linspace(60.0, 90.0, n), t_is)])
        outdoor = OutdoorBoundary(state=State.init(t=0.0 + ATP, rh=80.0))
        indoor = IndoorBoundary(state=State.init(t=20.0 + ATP, rh=50.0))
        j_v_ks = vapour_flow_ks(g, t_is, mu_is, outdoor=outdoor, indoor=indoor)
        states = [outdoor.state] + [State(t=t_i, mu=mu_i) for t_i, mu_i in zip(t_is, mu_is)] + [indoor.state]
        for k, link in enumerate(g.links):
            left, right = states[k], states[k + 1]
            assert j_v_ks[k] == pytest.approx((left.p_v - right.p_v) / link.r_m(left, right))

    def test_number(self):
        g = _one_layer_geometry()
        t = 20.0 + ATP
        t_is, mu_is = _uniform(g, t, 50.0)
        j_v_ks = vapour_flow_ks(g, t_is, mu_is, outdoor=_outdoor(t), indoor=_indoor(t))
        assert len(j_v_ks) == len(g.links)


def _plywood_gw_geometry() -> WallGeometry:
    """2 層の壁：構造用合板1 9 mm（分割数 6）＋ グラスウール1 100 mm（分割数 5）、接触 50・7.75e-7。"""
    m = {'source': 'whamcavity', 'initial_temperature': 20.0, 'initial_rh': 50.0}
    return WallGeometry.from_input(WallInput.from_dict({
        'surface': {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2},
        'layers': [m | {'name': '構造用合板1', 'thickness': 0.009, 'n_div': 6},
                   m | {'name': 'グラスウール1', 'thickness': 0.1, 'n_div': 5}],
        'interfaces': [{'cond_h': 22.4, 'cond_m': 2.0e-11}, {'cond_h': 50.0, 'cond_m': 7.75e-7}, {'cond_h': 9.2, 'cond_m': 2.6e-10}],
        'len_vertical': 1.0,
        'len_horizontal': 1.0,
        'height': 1.0,
    }))


def _mu_is(t: float, rh_is: np.ndarray) -> np.ndarray:
    """温度 t（K）一定で、相対湿度 rh_is（%）の質点の水分化学ポテンシャル, J/kg, [i]。"""
    return np.array([get_wp(rh=rh_i, t=t) for rh_i in rh_is])


class TestLiquidFlow:

    def test_interface(self):
        # 合板 + GW の 2 層：湿度が高く μ に差があっても、境目（表面・層と層）のつながりの液水の流れは 0
        g = _plywood_gw_geometry()
        t = 20.0 + ATP
        rh_is = np.linspace(99.5, 98.0, len(g.nodes))
        j_l_ks = liquid_flow_ks(g, np.full(len(g.nodes), t), _mu_is(t, rh_is),
                                outdoor=OutdoorBoundary(state=State.init(t=t, rh=100.0)),
                                indoor=IndoorBoundary(state=State.init(t=t, rh=50.0)))
        # 境目のつながり：0 番目（外表面）、6 番目（合板と GW の間）、最後（内表面）
        for k in (0, 6, len(g.links) - 1):
            assert j_l_ks[k] == 0.0

    def test_no_liquid(self):
        # 構造用合板1 は RH 50% 前後では液水が動かない：μ に差があっても、すべてのつながりで 0
        g = _one_layer_geometry()
        t = 20.0 + ATP
        rh_is = np.linspace(55.0, 45.0, len(g.nodes))
        j_l_ks = liquid_flow_ks(g, np.full(len(g.nodes), t), _mu_is(t, rh_is), outdoor=_outdoor(t), indoor=_indoor(t))
        np.testing.assert_array_equal(j_l_ks, 0.0)

    def test_liquid(self):
        # 構造用合板1、外気側の質点 RH 99.5% → 室内側 98%：層の中で湿った側から乾いた側へ（正の向きに）流れる
        g = _one_layer_geometry()
        t = 20.0 + ATP
        n = len(g.nodes)
        mu_is = _mu_is(t, np.linspace(99.5, 98.0, n))
        t_is = np.full(n, t)
        outdoor, indoor = _outdoor(t), _indoor(t)
        j_l_ks = liquid_flow_ks(g, t_is, mu_is, outdoor=outdoor, indoor=indoor)

        # 層の中のつながり（1〜n-1 番目）は正の向きに流れ、値は (μ_左 - μ_右) / link.r_l(左, 右)
        for k in range(1, n):
            left, right = State(t=t, mu=mu_is[k - 1]), State(t=t, mu=mu_is[k])
            assert j_l_ks[k] > 0.0
            assert j_l_ks[k] == pytest.approx((left.mu - right.mu) / g.links[k].r_l(left, right))

        # 表面のつながりは 0
        assert (j_l_ks[0], j_l_ks[-1]) == (0.0, 0.0)

    def test_number(self):
        g = _one_layer_geometry()
        t = 20.0 + ATP
        t_is, mu_is = _uniform(g, t, 50.0)
        assert len(liquid_flow_ks(g, t_is, mu_is, outdoor=_outdoor(t), indoor=_indoor(t))) == len(g.links)


class TestWaterAmountAndHeatCapacityIs:

    def test_same_as_nodes(self):
        # まとめて計算した値が、質点ごとのメソッドの値と一致する（通気層を含む壁）
        g = _plywood_gw_geometry()
        n = len(g.nodes)
        t_is = np.linspace(5.0, 15.0, n) + ATP
        mu_is = np.array([get_wp(rh=rh_i, t=t_i) for rh_i, t_i in zip(np.linspace(60.0, 90.0, n), t_is)])
        states = [State(t=t_i, mu=mu_i) for t_i, mu_i in zip(t_is, mu_is)]
        np.testing.assert_allclose(water_amount_is(g, t_is, mu_is), [node.water_amount(s) for node, s in zip(g.nodes, states)])
        np.testing.assert_allclose(heat_capacity_is(g, t_is, mu_is), [node.heat_capacity(s) for node, s in zip(g.nodes, states)])

    def test_total_water(self):
        # 一様な 1 層の壁：水分量の合計 = 厚さ × 乾燥密度 × u(φ)
        g = _one_layer_geometry()
        t = 20.0 + ATP
        t_is, mu_is = _uniform(g, t, 70.0)
        m = g.nodes[0].material
        assert water_amount_is(g, t_is, mu_is).sum() == pytest.approx(0.009 * m.rho * m.get_u(70.0))
