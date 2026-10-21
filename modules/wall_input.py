"""壁の入力（確認済みの値だけを持つ部品）。

入力の dict から作り、値がそろっていておかしくないことを、作るときに 1 回だけ確かめる。
作ったあとは値を変えない（frozen）。計算する部品は、ここで確かめた値だけを受け取る。

段階 1（docs/design/class_structure.md）で作る。今の input_wall.py・wall.Layer は、置き換えが終わったら消す。
"""

from dataclasses import dataclass

from modules.material_loaders import MATERIAL_SOURCES


# 材料の層の入力の dict のキー（すべて必ず指定する）
_MATERIAL_LAYER_KEYS = ('source', 'name', 'thickness', 'n_div', 'initial_temperature', 'initial_rh')

# 通気層の入力の dict のキー（すべて必ず指定する。'air_layer' は True）
_AIR_LAYER_KEYS = ('air_layer', 'thickness', 'alpha', 'initial_temperature', 'initial_rh')

# 境目の入力の dict のキー（すべて必ず指定する）
_INTERFACE_KEYS = ('cond_h', 'cond_m')


def _check_keys(d: dict, required: tuple[str, ...], where: str):
    """dict のキーを確かめる。必ず指定するキーがない、または知らないキー（打ち間違いなど）があればエラーにする。

    Args:
        d: 入力の dict
        required: 必ず指定するキー（これ以外のキーは使えない）
        where: エラーのメッセージに出す、どの入力か
    """

    # 必ず指定するキーのうち、dict にないものを集める。1 つでもあればエラー
    missing = [k for k in required if k not in d]
    if missing:
        raise ValueError(f'{where} に {missing} がありません。')

    # dict のキーのうち、使えるキーにないもの（打ち間違いなど）を集める。1 つでもあればエラー
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

        # 出どころが、材料を読み込める Excel（'whamcavity'・'mews_ashrae'）のどれかでなければエラー
        if self.source not in MATERIAL_SOURCES:
            raise ValueError(f'材料の出どころ source は {list(MATERIAL_SOURCES)} のどれかにしてください（{self.source!r}）。')

        # 名称が文字列でない、または空の文字列ならエラー
        if not isinstance(self.name, str) or self.name == '':
            raise ValueError(f'材料の名称 name を指定してください（{self.name!r}）。')

        # 厚さが 0 より大きくなければエラー
        # （「not ... > 0」と書くのは、数値でない値（NaN など）も「0 より大きい」にならず、エラーになるようにするため）
        if not self.thickness > 0.0:
            raise ValueError(f'厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # 分割数が、真偽値（True・False）、整数でない値、2 より小さい値のどれかならエラー
        # （真偽値を先に除くのは、Python では True・False が整数の 1・0 として扱われ、整数の確認を通ってしまうため）
        if isinstance(self.n_div, bool) or not isinstance(self.n_div, int) or self.n_div < 2:
            raise ValueError(f'分割数 n_div は 2 以上の整数にしてください（{self.n_div!r}）。層の両端に質点を置くため。')

        # 初期の相対湿度が 0 より大きく 100 より小さくなければエラー
        # （0% と 100% では水分化学ポテンシャルが無限大になり、計算できないため）
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


@dataclass(frozen=True, kw_only=True)
class AirLayerInput:
    """通気層 1 枚分の入力。

    材料を持たない（空気として扱う）。分割数は 1（よく混ざった空気の 1 つの質点）。
    層と通気層の境目の値（通気層の中の伝達率）は、ここではなく境目の入力が持つ。
    """

    # 厚さ, m
    thickness: float

    # 流量係数, -（相当開口面積 = α × 厚さ × 壁の横の長さ）
    alpha: float

    # 初期の温度, deg.C
    initial_temperature: float

    # 初期の相対湿度, %
    initial_rh: float

    @property
    def n_div(self) -> int:
        """分割数。通気層は 1 に決まっている（入力では受け取らない）。"""
        return 1

    def __post_init__(self):
        """作るときに値を確かめる。α = 0（換気のない空気層）は許す。"""

        # 厚さが 0 より大きくなければエラー（MaterialLayerInput と同じ）
        if not self.thickness > 0.0:
            raise ValueError(f'厚さ thickness は 0 より大きくしてください（{self.thickness}）。')

        # 流量係数が 0 以上でなければエラー（0 は換気のない空気層として許す）
        if not self.alpha >= 0.0:
            raise ValueError(f'流量係数 alpha は 0 以上にしてください（{self.alpha}）。')

        # 初期の相対湿度が 0 より大きく 100 より小さくなければエラー（MaterialLayerInput と同じ）
        if not 0.0 < self.initial_rh < 100.0:
            raise ValueError(f'初期の相対湿度 initial_rh は 0 より大きく 100 より小さくしてください（{self.initial_rh}）。')

    @classmethod
    def from_dict(cls, d: dict) -> 'AirLayerInput':
        """dict から作る。

        Args:
            d: {'air_layer': True, 'thickness', 'alpha', 'initial_temperature', 'initial_rh'}（すべて必ず指定する）
        """

        _check_keys(d, _AIR_LAYER_KEYS, where='通気層の入力')

        # 'air_layer' の値が True でなければエラー（材料の層なら、このキー自体を書かない決まり）
        if d['air_layer'] is not True:
            raise ValueError(f"通気層の入力の 'air_layer' は True にしてください（{d['air_layer']!r}）。")

        return cls(**{k: d[k] for k in _AIR_LAYER_KEYS if k != 'air_layer'})


# 層の入力：材料の層か通気層のどちらか
LayerInput = MaterialLayerInput | AirLayerInput


def layer_input_from_dict(d: dict) -> LayerInput:
    """dict から層の入力を作る。'air_layer' のキーがあれば通気層、なければ材料の層として作る。

    Args:
        d: 材料の層なら MaterialLayerInput.from_dict、通気層なら AirLayerInput.from_dict の形の dict
    """

    # 'air_layer' のキーがあれば通気層
    if 'air_layer' in d:

        # 値が True でなければエラー（材料の層なら、このキー自体を書かない決まり）
        # 先にここで確かめるのは、材料の層の dict に 'air_layer': False を書いたとき、
        # 通気層のキーの不足（'alpha' がない など）ではなく、'air_layer' の書き方の誤りとして知らせるため
        if d['air_layer'] is not True:
            raise ValueError(f"層の入力の 'air_layer' は、通気層なら True、材料の層なら書かないでください（{d['air_layer']!r}）。")

        return AirLayerInput.from_dict(d)

    # なければ材料の層
    return MaterialLayerInput.from_dict(d)


@dataclass(frozen=True, kw_only=True)
class InterfaceInput:
    """境目 1 つ分の入力（外気と最初の層、層と層、最後の層と室内）。

    層が n 枚なら、境目は n + 1 個ある。境目ごとに 1 つの値を持つ（両側の層が別々に持たない）。
    表面の伝達、層と層の接触、材料と通気層の間の伝達、塗膜・防湿層などの抵抗を、1 つのコンダクタンスにまとめて持つ。
    境目では液水は移動しない（液水のコンダクタンスを持たない。Fortran・今のコードと同じ扱い）。
    """

    # 熱コンダクタンス, W/(m2 K)
    cond_h: float

    # 湿気コンダクタンス, kg/(m2 s Pa)
    cond_m: float

    def __post_init__(self):
        """作るときに値を確かめる。値の大きさが「ふつうの範囲」かどうかは確かめない（0 以下だけを防ぐ）。"""

        # 熱コンダクタンスが 0 より大きくなければエラー（0 だと境目の両側が熱的につながらず、抵抗が 1/0 になる）
        if not self.cond_h > 0.0:
            raise ValueError(f'熱コンダクタンス cond_h は 0 より大きくしてください（{self.cond_h}）。')

        # 湿気コンダクタンスが 0 より大きくなければエラー（防湿層は 2.0e-11 などの小さい値で表す）
        if not self.cond_m > 0.0:
            raise ValueError(f'湿気コンダクタンス cond_m は 0 より大きくしてください（{self.cond_m}）。')

    @classmethod
    def from_dict(cls, d: dict) -> 'InterfaceInput':
        """dict から作る。

        Args:
            d: {'cond_h', 'cond_m'}（すべて必ず指定する）
        """

        _check_keys(d, _INTERFACE_KEYS, where='境目の入力')

        return cls(**{k: d[k] for k in _INTERFACE_KEYS})
