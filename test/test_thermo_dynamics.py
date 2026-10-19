import math

import pytest


from modules import thermo_dynamics


def test_get_lambda_dsh_mu_l():
    """液相水分伝導率が、手で計算した値と一致することを確認する。

    含水率 u = 相対湿度(0～1)、液水拡散係数 1e-8 m2/s（一定）とする。
    """

    rh = 95.0
    t = 293.15

    # 液相水分伝導率 = 水の密度 × 液水拡散係数 × |Δu / Δμ|
    # Δu = (95.005 - 94.995) * 0.01、Δμ = RG · T · (ln 0.95005 - ln 0.94995)
    du = (95.005 - 94.995) * 0.01
    dmu = thermo_dynamics.RG * t * (math.log(0.95005) - math.log(0.94995))
    expected = 998.0 * 1e-8 * abs(du / dmu)

    actual = thermo_dynamics.get_lambda_dsh_mu_l(rh=rh, t=t, get_u=lambda r: r * 0.01, d_w=lambda u: 1e-8)

    assert actual == pytest.approx(expected, rel=1e-9)


def test_get_lambda_dsh_mu_l_no_liquid():
    """液水拡散係数が 0 のとき、液相水分伝導率が 0 になることを確認する。"""

    actual = thermo_dynamics.get_lambda_dsh_mu_l(rh=95.0, t=293.15, get_u=lambda r: r * 0.01, d_w=lambda u: 0.0)

    assert actual == 0.0
