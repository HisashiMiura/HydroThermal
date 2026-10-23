import numpy as np

from modules.wall_builder import build_wall
from modules.wall_geometry import AirNode, material_finder
from modules.wall_input import WallInput


def _main_wall_dict() -> dict:
    """今の main.py・Fortran の入力の壁の dict（test_wall_geometry.py の _main_wall_dict と同じ壁）。"""

    def m(name, thickness, n_div, temperature, rh):
        return {'source': 'whamcavity', 'name': name, 'thickness': thickness, 'n_div': n_div,
                'initial_temperature': temperature, 'initial_rh': rh}

    return {
        'surface': {'direction': 'e', 'angle': 90.0, 'albedo': 0.3, 'absorptance': 0.9, 'emissivity': 0.9, 'eva_height': 4.2},
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
        'len_vertical': 7.0,
        'len_horizontal': 0.42,
        'height': 7.0,
    }


def _build():
    return build_wall(WallInput.from_dict(_main_wall_dict()))


class TestBuildWall:

    def test_size(self):
        # 今の壁：質点 33 個、状態の長さも 33
        geometry, state = _build()
        assert (len(geometry.nodes), len(state)) == (33, 33)

    def test_initial_temperature(self):
        # サイディング（質点 0〜4）・通気層（5）は 15 deg.C、それ以外は 10 deg.C
        _, state = _build()
        expected = [15.0] * 6 + [10.0] * 27
        np.testing.assert_allclose(state.theta_is, expected)

    def test_initial_rh(self):
        # 合板（質点 11〜16、22〜27）は 80%、それ以外は 50%
        _, state = _build()
        expected = np.full(33, 50.0)
        expected[11:17] = 80.0
        expected[22:28] = 80.0
        np.testing.assert_allclose(state.rh_is, expected)

    def test_air_node(self):
        # 質点 5 は空気の質点で、初期値は通気層の値（15 deg.C・50%）
        geometry, state = _build()
        assert isinstance(geometry.nodes[5], AirNode)
        state_i = state.state(5)
        assert (round(state_i.theta, 10), round(state_i.rh, 10)) == (15.0, 50.0)

    def test_find_material(self):
        # 渡した材料を探す関数が、壁の形を作るときに使われる
        called = []
        excel = material_finder()

        def recording_find(source, name):
            called.append(name)
            return excel(source, name)

        build_wall(WallInput.from_dict(_main_wall_dict()), find_material=recording_find)
        assert len(called) == 6
