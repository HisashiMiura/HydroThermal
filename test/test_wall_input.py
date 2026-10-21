import dataclasses

import pytest

from modules.wall_input import MaterialLayerInput, AirLayerInput, layer_input_from_dict


def _material_layer() -> MaterialLayerInput:
    """材料の層の正しい入力（構造用合板1、9 mm）。"""
    return MaterialLayerInput(source='whamcavity', name='構造用合板1', thickness=0.009, n_div=6,
                      initial_temperature=10.0, initial_rh=80.0)


class TestMaterialLayerInput:

    def test_values(self):
        layer = _material_layer()
        assert (layer.source, layer.name, layer.thickness, layer.n_div) == ('whamcavity', '構造用合板1', 0.009, 6)
        assert (layer.initial_temperature, layer.initial_rh) == (10.0, 80.0)

    def test_frozen(self):
        # 作ったあとは値を変えられない
        layer = _material_layer()
        with pytest.raises(dataclasses.FrozenInstanceError):
            layer.thickness = 0.1

    def test_keyword_only(self):
        # 名前を付けずに（位置で）値を渡すとエラー（順番の間違いを防ぐ）
        with pytest.raises(TypeError):
            MaterialLayerInput('whamcavity', '構造用合板1', 0.009, 6, 10.0, 80.0)


def _material_layer_dict() -> dict:
    """材料の層の正しい入力の dict（構造用合板1、9 mm）。"""
    return {'source': 'whamcavity', 'name': '構造用合板1', 'thickness': 0.009, 'n_div': 6,
            'initial_temperature': 10.0, 'initial_rh': 80.0}


class TestMaterialLayerInputFromDict:

    def test_read(self):
        # dict から作ったものと、直接作ったものが同じ
        assert MaterialLayerInput.from_dict(_material_layer_dict()) == _material_layer()

    @pytest.mark.parametrize('key', ['source', 'name', 'thickness', 'n_div', 'initial_temperature', 'initial_rh'])
    def test_missing_key(self, key):
        d = _material_layer_dict()
        del d[key]
        with pytest.raises(ValueError, match=key):
            MaterialLayerInput.from_dict(d)

    def test_unknown_key(self):
        d = _material_layer_dict()
        d['thicknes'] = 0.01
        with pytest.raises(ValueError, match='thicknes'):
            MaterialLayerInput.from_dict(d)


class TestMaterialLayerInputValues:

    @pytest.mark.parametrize('key, value', [
        ('source', 'excel'),
        ('name', ''),
        ('thickness', 0.0),
        ('thickness', -0.01),
        ('n_div', 1),
        ('n_div', 2.5),
        ('n_div', True),
        ('initial_rh', 0.0),
        ('initial_rh', 100.0),
    ])
    def test_invalid_value(self, key, value):
        d = _material_layer_dict()
        d[key] = value
        with pytest.raises(ValueError, match=key):
            MaterialLayerInput.from_dict(d)

    def test_n_div_2(self):
        # 分割数 2（両端だけ）は作れる
        d = _material_layer_dict()
        d['n_div'] = 2
        assert MaterialLayerInput.from_dict(d).n_div == 2


def _air_layer_dict() -> dict:
    """通気層の正しい入力の dict（25 mm、α = 0.085）。"""
    return {'air_layer': True, 'thickness': 0.025, 'alpha': 0.085, 'initial_temperature': 15.0, 'initial_rh': 50.0}


class TestAirLayerInput:

    def test_read(self):
        layer = AirLayerInput.from_dict(_air_layer_dict())
        assert (layer.thickness, layer.alpha, layer.n_div) == (0.025, 0.085, 1)
        assert (layer.initial_temperature, layer.initial_rh) == (15.0, 50.0)

    def test_frozen(self):
        layer = AirLayerInput.from_dict(_air_layer_dict())
        with pytest.raises(dataclasses.FrozenInstanceError):
            layer.alpha = 0.1

    def test_alpha_0(self):
        # α = 0（換気のない空気層）は作れる
        d = _air_layer_dict()
        d['alpha'] = 0.0
        assert AirLayerInput.from_dict(d).alpha == 0.0

    @pytest.mark.parametrize('key', ['air_layer', 'thickness', 'alpha', 'initial_temperature', 'initial_rh'])
    def test_missing_key(self, key):
        d = _air_layer_dict()
        del d[key]
        with pytest.raises(ValueError, match=key):
            AirLayerInput.from_dict(d)

    @pytest.mark.parametrize('key, value', [
        ('air_layer', False),
        ('thickness', 0.0),
        ('alpha', -0.1),
        ('initial_rh', 0.0),
        ('initial_rh', 100.0),
    ])
    def test_invalid_value(self, key, value):
        d = _air_layer_dict()
        d[key] = value
        with pytest.raises(ValueError, match=key):
            AirLayerInput.from_dict(d)

    @pytest.mark.parametrize('key', ['name', 'source', 'n_div'])
    def test_not_allowed_key(self, key):
        # 通気層には材料も分割数も指定できない
        d = _air_layer_dict()
        d[key] = 'x'
        with pytest.raises(ValueError, match=key):
            AirLayerInput.from_dict(d)


class TestLayerInputFromDict:

    def test_material_layer(self):
        # 'air_layer' がなければ材料の層
        layer = layer_input_from_dict(_material_layer_dict())
        assert isinstance(layer, MaterialLayerInput)
        assert layer == MaterialLayerInput.from_dict(_material_layer_dict())

    def test_air_layer(self):
        # 'air_layer': True なら通気層
        layer = layer_input_from_dict(_air_layer_dict())
        assert isinstance(layer, AirLayerInput)
        assert layer == AirLayerInput.from_dict(_air_layer_dict())

    def test_air_layer_false(self):
        # 'air_layer': False は、材料の層としては読まず、エラーにする
        d = _material_layer_dict()
        d['air_layer'] = False
        with pytest.raises(ValueError, match='air_layer'):
            layer_input_from_dict(d)
