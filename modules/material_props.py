import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FormulaIsotherm:
    """式の文字列で与える平衡含水率曲線（materials_whamcavity.xlsx 用）。

    式の中では、相対湿度（0.0～1.0）を変数 r で、数学関数を math.xxx で書く。
    例: '1.58*r**1.3664*math.exp(-2.1708*(1-r**90.988))'
    """

    # 含水率の式
    formula: str

    def u(self, x: float) -> float:
        """相対湿度から質量含水率を求める。

        Args:
            x: 相対湿度(0.0～1.0)

        Returns:
            質量含水率, kg/kg
        """

        return eval(self.formula, {'math': math}, {'r': x})
