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


@dataclass(frozen=True)
class PowerExpIsotherm:
    """係数で与える平衡含水率曲線（materials_mews_ashrae.xlsx 用）。

    u = a · x^b · exp(c · (1 − x^d))    x: 相対湿度(0.0～1.0)

    a は相対湿度 100% のときの含水率になる（x = 1 のとき u = a）。
    式は materials_mews_ashrae.xlsx の「平衡含水率」シートの式に合わせた。
    """

    # 係数, kg/kg
    a: float

    # 係数, -
    b: float

    # 係数, -
    c: float

    # 係数, -
    d: float

    def u(self, x: float) -> float:
        """相対湿度から質量含水率を求める。

        Args:
            x: 相対湿度(0.0～1.0)

        Returns:
            質量含水率, kg/kg
        """

        return self.a * x**self.b * math.exp(self.c * (1 - x**self.d))


@dataclass(frozen=True)
class ConstantVaporConductivity:
    """相対湿度によらず一定の湿気伝導率。"""

    # 湿気伝導率, (kg/s)/(m Pa)
    value: float

    def lambda_dsh_m(self, x: float) -> float:
        """湿気伝導率を求める。

        Args:
            x: 相対湿度(0.0～1.0)（一定値なので使わない）

        Returns:
            湿気伝導率, (kg/s)/(m Pa)
        """

        return self.value


@dataclass(frozen=True)
class PowerExpVaporConductivity:
    """相対湿度によって変わる湿気伝導率。

    λ' = a · x^b · exp(c · (1 − x^d))    x: 相対湿度(0.0～1.0)

    a は相対湿度 100% のときの値になる（x = 1 のとき λ' = a）。
    """

    # 係数, (kg/s)/(m Pa)
    a: float

    # 係数, -
    b: float

    # 係数, -
    c: float

    # 係数, -
    d: float

    def lambda_dsh_m(self, x: float) -> float:
        """湿気伝導率を求める。

        Args:
            x: 相対湿度(0.0～1.0)

        Returns:
            湿気伝導率, (kg/s)/(m Pa)
        """

        return self.a * x**self.b * math.exp(self.c * (1 - x**self.d))


@dataclass(frozen=True)
class NoLiquidDiffusivity:
    """液水が移動しない材料の液水拡散係数。常に 0 を返す。"""

    def d_w(self, u: float) -> float:
        """液水拡散係数を求める。

        Args:
            u: 質量含水率, kg/kg（液水が移動しないので使わない）

        Returns:
            液水拡散係数, m2/s
        """

        return 0.0


@dataclass(frozen=True)
class PiecewiseExpPolyDiffusivity:
    """含水率の区間ごとに式を切り替える液水拡散係数。

    各区間の式は次のとおり。
        D = exp(a + b·u + c·u^2 + d·u^3 + e·u^4 + f·u^5 + g·u^6)    u: 質量含水率, kg/kg

    区間を前から順に調べ、含水率が「下限を超え、上限以下」に入る最初の区間の式を使う。
    どの区間にも入らなければ 0（液水が移動しない）とする。
    境目ちょうどの含水率は、下側の区間に入る。

    例: 含水率 0.45 を超え 1.10 以下のときだけ D = exp(-30.91 + 4.2967·u - 0.22017·u^2) とする場合
        PiecewiseExpPolyDiffusivity(ranges=(
            (0.45, 1.10, (-30.91, 4.2967, -0.22017, 0, 0, 0, 0)),
        ))

    例: 含水率によらず1本の式を使う場合は、下限・上限を無限大にする。
        PiecewiseExpPolyDiffusivity(ranges=(
            (-math.inf, math.inf, (-32.285, 272.18, 0, 0, 0, 0, 0)),
        ))
    """

    # (下限, 上限, 係数 (a, b, c, d, e, f, g)) の組。下限・上限は質量含水率, kg/kg。使わない次数の係数は 0 とする。
    ranges: tuple[tuple[float, float, tuple[float, float, float, float, float, float, float]], ...]

    def __post_init__(self):

        for lower, upper, coefficients in self.ranges:

            if len(coefficients) != 7:
                raise ValueError(f'係数は a～g の7個を指定してください: {coefficients}')

            if not lower < upper:
                raise ValueError(f'下限は上限より小さくしてください: 下限={lower}, 上限={upper}')

    def d_w(self, u: float) -> float:
        """液水拡散係数を求める。

        Args:
            u: 質量含水率, kg/kg

        Returns:
            液水拡散係数, m2/s
        """

        for lower, upper, coefficients in self.ranges:

            if lower < u <= upper:

                a, b, c, d, e, f, g = coefficients

                return math.exp(a + b * u + c * u**2 + d * u**3 + e * u**4 + f * u**5 + g * u**6)

        # どの区間にも入らない
        return 0.0
