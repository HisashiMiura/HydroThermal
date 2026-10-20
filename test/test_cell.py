import math

import pytest


from modules.cell import (
    CellAirLayer,
    CellOutsideSurface,
    CellInsideSurface,
    CellOutsideEndPoint,
    CellInsideEndPoint,
    CellOutsideEndPointAirLayer,
    CellInsideEndPointAirLayer,
    CellInterior,
)
from modules.materials import Materials
from modules.material_loaders import load_whamcavity, load_mews_ashrae
from modules.state import State
from modules.thermo_dynamics import COND_M_I, COND_M_O, COND_M_AIR


_whamcavity = Materials(load_whamcavity())
_mews_ashrae = Materials(load_mews_ashrae())

# セルの幅, m
_X = 0.01

# 確認する相対湿度, %
_RHS = [30.0, 60.0, 90.0]


def _state(rh: float) -> State:
    """温度 20 ℃、相対湿度 rh % の状態を作る。"""
    return State.init(t=293.15, rh=rh)


def _plywood1_lambda_dsh_m(rh: float) -> float:
    """構造用合板1 の湿気伝導率, (kg/s)/(m Pa)。Fortran（Whamcavity.f95 763行目）の式を書き写したもの。

    Args:
        rh: 相対湿度, %
    """
    d1 = rh * 0.01
    return 1.87E-11 * d1**2.4019 * math.exp(-0.78864 * (1 - d1**1.1471))


@pytest.mark.parametrize('rh', _RHS)
def test_interior_r_m_plywood1(rh):
    """CellInterior の透湿抵抗が、その状態の相対湿度での湿気伝導率で決まることを確認する（構造用合板1）。"""

    cell = CellInterior(x=_X, material=_whamcavity.get_material('構造用合板1'))
    state = _state(rh)

    expected = _X / _plywood1_lambda_dsh_m(state.rh) / 2

    assert cell.r_m_mns(state=state) == pytest.approx(expected, rel=1e-12)
    assert cell.r_m_pls(state=state) == pytest.approx(expected, rel=1e-12)


def test_interior_r_m_plywood1_depends_on_rh():
    """構造用合板1 の透湿抵抗は、湿度が高いほど小さくなることを確認する。"""

    cell = CellInterior(x=_X, material=_whamcavity.get_material('構造用合板1'))

    r = [cell.r_m_pls(state=_state(rh)) for rh in _RHS]

    assert r[0] > r[1] > r[2]


@pytest.mark.parametrize('rh', _RHS)
def test_interior_r_m_constant(rh):
    """固定値の材料（グラスウール1）では、どの湿度でも「幅 ÷ 旧 Excel の固定値 ÷ 2」（変更前と同じ値）になることを確認する。"""

    m = _whamcavity.get_material('グラスウール1')
    cell = CellInterior(x=_X, material=m)
    state = _state(rh)

    assert cell.r_m_mns(state=state) == _X / m.vapor_conductivity.value / 2
    assert cell.r_m_pls(state=state) == _X / m.vapor_conductivity.value / 2


@pytest.mark.parametrize('rh', _RHS)
def test_surface_and_end_point_r_m(rh):
    """表面・端のセルで、材料側は湿度で決まる値、外側は今と同じ定数になることを確認する（構造用合板1）。"""

    m = _whamcavity.get_material('構造用合板1')
    state = _state(rh)
    expected = _X / _plywood1_lambda_dsh_m(state.rh)

    cell = CellOutsideSurface(x=_X, material=m)
    assert cell.r_m_mns(state=state) == 1 / COND_M_O
    assert cell.r_m_pls(state=state) == pytest.approx(expected, rel=1e-12)

    cell = CellInsideSurface(x=_X, material=m)
    assert cell.r_m_mns(state=state) == pytest.approx(expected, rel=1e-12)
    assert cell.r_m_pls(state=state) == 1 / COND_M_I

    cell = CellOutsideEndPoint(x=_X, material=m, cond_h_o=10.0, cond_m_o=3.0e-8)
    assert cell.r_m_mns(state=state) == 1 / 3.0e-8
    assert cell.r_m_pls(state=state) == pytest.approx(expected, rel=1e-12)

    cell = CellInsideEndPoint(x=_X, material=m, cond_h_i=9.0, cond_m_i=2.0e-8)
    assert cell.r_m_mns(state=state) == pytest.approx(expected, rel=1e-12)
    assert cell.r_m_pls(state=state) == 1 / 2.0e-8

    cell = CellOutsideEndPointAirLayer(x=_X, material=m, ratio=1.0, v_threshold=0.0)
    assert cell.r_m_mns(state=state) == 1 / COND_M_AIR
    assert cell.r_m_pls(state=state) == pytest.approx(expected, rel=1e-12)

    cell = CellInsideEndPointAirLayer(x=_X, material=m, ratio=1.0, v_threshold=0.0)
    assert cell.r_m_mns(state=state) == pytest.approx(expected, rel=1e-12)
    assert cell.r_m_pls(state=state) == 1 / COND_M_AIR


def test_air_layer_r_m():
    """通気層の透湿抵抗は 0 のままであることを確認する。"""

    cell = CellAirLayer(x=_X, alpha_a=0.01, height=3.0)
    state = _state(60.0)

    assert cell.r_m_mns(state=state) == 0.0
    assert cell.r_m_pls(state=state) == 0.0


@pytest.mark.parametrize('rh', _RHS)
def test_interior_r_m_mews_ashrae(rh):
    """新しい Excel の材料（湿気伝導率は湿度で変わる式だけ）で、湿度で決まる透湿抵抗を計算できることを確認する。"""

    m = _mews_ashrae.get_material('ASHRAE Plywood -1')
    cell = CellInterior(x=_X, material=m)
    state = _state(rh)

    assert cell.r_m_pls(state=state) == pytest.approx(_X / m.vapor_conductivity.lambda_dsh_m(state.rh * 0.01) / 2, rel=1e-12)
