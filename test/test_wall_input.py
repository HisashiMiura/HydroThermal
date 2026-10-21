import dataclasses

import pytest

from modules.wall_input import MaterialLayerInput


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
