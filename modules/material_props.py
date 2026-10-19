import math
from dataclasses import dataclass
from functools import lru_cache
from types import CodeType


@lru_cache(maxsize=None)
def _compile(formula: str) -> CodeType:
    """式の文字列を、eval ですぐに実行できる形に変換する。

    同じ文字列なら、2回目以降は1回目に変換した結果をそのまま返す。
    """

    return compile(formula, '<isotherm>', 'eval')


@dataclass(frozen=True)
class FormulaIsotherm:
    """式の文字列で与える平衡含水率曲線（materials_whamcavity.xlsx 用）。

    式の中では、相対湿度（0.0～1.0）を変数 r で、数学関数を math.xxx で書く。
    例: '1.58*r**1.3664*math.exp(-2.1708*(1-r**90.988))'

    相対湿度によって式を切り替える場合は、conditional に (境目, 式) の組を並べる。
    前から順に調べ、相対湿度が境目を超えた最初の式を使う。どれにも当てはまらなければ formula を使う。

    例: 相対湿度 0.89 以下は式A、0.89 超 0.95 以下は式B、0.95 超は式C を使う場合
        FormulaIsotherm(
            formula='式A',
            conditional=(
                (0.95, '式C'),  # 0.95 を超えたら式C
                (0.89, '式B'),  # 0.89 を超えたら式B
            ),
        )

        r = 0.50 → どの境目も超えない → 式A
        r = 0.92 → 0.95 は超えない、0.89 は超える → 式B
        r = 0.97 → 0.95 を超える → 式C

    境目の大きい組から順に並べること。小さい組を先に置くと、それより後ろの組は使われなくなる。
    """

    # 基本の含水率の式
    formula: str

    # (境目, 式) の組。境目は相対湿度(0.0～1.0)。
    conditional: tuple[tuple[float, str], ...] = ()

    def __post_init__(self):

        # 式に書き間違いがあれば、ここでエラーにする
        _compile(self.formula)
        for _, formula in self.conditional:
            _compile(formula)

    def u(self, x: float) -> float:
        """相対湿度から質量含水率を求める。

        Args:
            x: 相対湿度(0.0～1.0)

        Returns:
            質量含水率, kg/kg
        """

        # 境目を超えた最初の式で計算する
        for threshold, formula in self.conditional:
            if x > threshold:
                return eval(_compile(formula), {'math': math}, {'r': x})

        return eval(_compile(self.formula), {'math': math}, {'r': x})
