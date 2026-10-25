import dataclasses

import pytest

from modules.boundary import NO_SUN, Boundaries, IndoorBoundary, OutdoorBoundary, SolarRadiation
from modules.state import State
from modules.thermo_dynamics import ATP


class TestBoundary:

    def test_outdoor(self):
        # 0 deg.C・80% から作ると、温度 273.15 K・相対湿度 80%
        outdoor = OutdoorBoundary.from_theta_rh(theta=0.0, rh=80.0)
        assert outdoor.state.t == pytest.approx(ATP)
        assert outdoor.state.rh == pytest.approx(80.0)

    def test_indoor(self):
        # 20 deg.C・50% から作ると、温度と相対湿度が元に戻る
        indoor = IndoorBoundary.from_theta_rh(theta=20.0, rh=50.0)
        assert indoor.state.theta == pytest.approx(20.0)
        assert indoor.state.rh == pytest.approx(50.0)

    def test_vapour_pressure(self):
        # 室内の水蒸気圧は、20 deg.C の飽和水蒸気圧（約 2339 Pa）の 50%
        indoor = IndoorBoundary.from_theta_rh(theta=20.0, rh=50.0)
        assert indoor.state.p_v == pytest.approx(0.5 * indoor.state.p_v_sat)
        assert indoor.state.p_v == pytest.approx(1170.0, rel=1e-2)

    def test_saturated(self):
        # 外気が相対湿度 100%（飽和）なら、水分化学ポテンシャルは 0
        outdoor = OutdoorBoundary.from_theta_rh(theta=5.0, rh=100.0)
        assert outdoor.state.mu == 0.0

    @pytest.mark.parametrize('rh', [0.0, 101.0])
    def test_invalid_rh(self, rh):
        with pytest.raises(ValueError, match='rh'):
            OutdoorBoundary.from_theta_rh(theta=0.0, rh=rh)

    def test_frozen(self):
        outdoor = OutdoorBoundary.from_theta_rh(theta=0.0, rh=80.0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            outdoor.state = State(t=300.0, mu=0.0)

    def test_not_state(self):
        # state に State 以外を渡すとエラー
        with pytest.raises(ValueError, match='室内'):
            IndoorBoundary(state=(293.15, -1.0e7))


class TestBoundaries:

    def test_make(self):
        # 外気と室内の組を作れる
        outdoor = OutdoorBoundary.from_theta_rh(theta=0.0, rh=80.0)
        indoor = IndoorBoundary.from_theta_rh(theta=20.0, rh=50.0)
        b = Boundaries(outdoor=outdoor, indoor=indoor)
        assert b.outdoor is outdoor
        assert b.indoor is indoor

    def test_swapped(self):
        # 外気と室内を取り違えるとエラー
        outdoor = OutdoorBoundary.from_theta_rh(theta=0.0, rh=80.0)
        indoor = IndoorBoundary.from_theta_rh(theta=20.0, rh=50.0)
        with pytest.raises(ValueError, match='outdoor'):
            Boundaries(outdoor=indoor, indoor=outdoor)


class TestSolarRadiation:

    def test_default(self):
        # 外気の日射の既定は、日射も夜間放射もない
        outdoor = OutdoorBoundary.from_theta_rh(theta=0.0, rh=80.0)
        assert outdoor.solar is NO_SUN
        assert (NO_SUN.i_dn, NO_SUN.i_sky, NO_SUN.r_n) == (0.0, 0.0, 0.0)

    def test_with_solar(self):
        solar = SolarRadiation(sin_h=0.5, cos_h=0.866, sin_a=0.0, cos_a=1.0, i_dn=600.0, i_sky=150.0, r_n=40.0)
        outdoor = OutdoorBoundary.from_theta_rh(theta=0.0, rh=80.0, solar=solar)
        assert outdoor.solar is solar

    @pytest.mark.parametrize('i_dn, i_sky', [(-1.0, 0.0), (0.0, -1.0)])
    def test_negative(self, i_dn, i_sky):
        # 日射量が負ならエラー
        with pytest.raises(ValueError, match='日射量'):
            SolarRadiation(sin_h=0.5, cos_h=0.866, sin_a=0.0, cos_a=1.0, i_dn=i_dn, i_sky=i_sky, r_n=0.0)

    def test_not_solar(self):
        # 外気の solar に SolarRadiation 以外を渡すとエラー
        with pytest.raises(ValueError, match='solar'):
            OutdoorBoundary(state=State(t=273.15, mu=-1.0e7), solar=(600.0, 150.0))
