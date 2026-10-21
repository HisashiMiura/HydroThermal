"""壁の入力（確認済みの値だけを持つ部品）。

入力の dict から作り、値がそろっていておかしくないことを、作るときに 1 回だけ確かめる。
作ったあとは値を変えない（frozen）。計算する部品は、ここで確かめた値だけを受け取る。

段階 1（docs/design/class_structure.md）で作る。今の input_wall.py・wall.Layer は、置き換えが終わったら消す。
"""

from dataclasses import dataclass

from modules.material_loaders import MATERIAL_SOURCES


# 材料の層の入力の dict のキー（すべて必ず指定する）
_MATERIAL_LAYER_KEYS = ('source', 'name', 'thickness', 'n_div', 'initial_temperature', 'initial_rh')


def _check_keys(d: dict, required: tuple[str, ...], where: str):
    """dict のキーを確かめる。必ず指定するキーがない、または知らないキー（打ち間違いなど）があればエラーにする。

    Args:
        d: 入力の dict
        required: 必ず指定するキー（これ以外のキーは使えない）
        where: エラーのメッセージに出す、どの入力か
    """

    missing = [k for k in required if k not in d]
    if missing:
        raise ValueError(f'{where} に {missing} がありません。')

    unknown = sorted(set(d) - set(required))
    if unknown:
        raise ValueError(f'{where} に知らないキー {unknown} があります（使えるキー: {list(required)}）。')


@dataclass(frozen=True, kw_only=True)
class MaterialLayerInput:
    """材料の層 1 枚分の入力。

    層と層・層と空気の境目の値（接触・表面のコンダクタンス）は、ここではなく境目の入力が持つ。
    """

    # 材料の出どころ（material_loaders.MATERIAL_SOURCES のキー）
    source: str

    # 材料の名称
    name: str

    # 厚さ, m
    thickness: float

    # 分割数（質点の数）。層の両端に質点を置く
    n_div: int

    # 初期の温度, deg.C
    initial_temperature: float

    # 初期の相対湿度, %
    initial_rh: float

    def __post_init__(self):
        """作るときに値を確かめる（直接作っても、from_dict で作っても働く）。

        材料の名称が実際にその出どころにあるかは、材料を読み込むとき（壁の形を作るとき）に確かめる。
        初期の温度は決まった範囲がないので確かめない。
        """

        if self.source not in MATERIAL_SOURCES:
            raise ValueError(f'材料の出どころ source は {list(MATERIAL_SOURCES)} のどれかにしてください（{self.source!r}）。')

        if not isinstance(self.name, str) or self.name == '':
            raise ValueError(f'材料の名称 name を指定してください（{self.name!r}）。')

        if not self.thickness > 0.0:
            raise ValueError(f'厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # bool は整数の 1・0 として扱われるので除く
        if isinstance(self.n_div, bool) or not isinstance(self.n_div, int) or self.n_div < 2:
            raise ValueError(f'分割数 n_div は 2 以上の整数にしてください（{self.n_div!r}）。層の両端に質点を置くため。')

        if not 0.0 < self.initial_rh < 100.0:
            raise ValueError(f'初期の相対湿度 initial_rh は 0 より大きく 100 より小さくしてください（{self.initial_rh}）。')

    @classmethod
    def from_dict(cls, d: dict) -> 'MaterialLayerInput':
        """dict から作る。

        Args:
            d: {'source', 'name', 'thickness', 'n_div', 'initial_temperature', 'initial_rh'}（すべて必ず指定する）
        """

        _check_keys(d, _MATERIAL_LAYER_KEYS, where='材料の層の入力')

        return cls(**{k: d[k] for k in _MATERIAL_LAYER_KEYS})
