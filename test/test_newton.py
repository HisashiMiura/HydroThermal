import numpy as np
import pytest

from modules.newton import banded_jacobian


def _to_banded(a: np.ndarray, l: int, u: int) -> np.ndarray:
    """ふつうの形の行列を、帯の詰めた形にする（J の p 行 q 列は ab[u + p - q, q]）。"""
    n = a.shape[0]
    ab = np.zeros((l + u + 1, n))
    for p in range(n):
        for q in range(max(0, p - l), min(n, p + u + 1)):
            ab[u + p - q, q] = a[p, q]
    return ab


def _random_banded_matrix(n: int, l: int, u: int, seed: int = 0) -> np.ndarray:
    """帯の部分だけに値がある、ふつうの形の行列。"""
    rng = np.random.default_rng(seed)
    a = rng.uniform(1.0, 2.0, size=(n, n))
    for p in range(n):
        for q in range(n):
            if not (-u <= p - q <= l):
                a[p, q] = 0.0
    return a


class TestBandedJacobian:

    @pytest.mark.parametrize('l, u', [(1, 1), (3, 3)])
    def test_linear(self, l, u):
        # 1 次式 F = A x - b のヤコビ行列は A そのもの（三重対角と、熱と水分を一緒に解くときの幅 3）
        n = 10
        a = _random_banded_matrix(n, l, u)
        b = np.arange(n, dtype=float)
        x_ps = np.linspace(-1.0, 1.0, n)
        f_ps, ab = banded_jacobian(lambda x: a @ x - b, x_ps, l=l, u=u)
        np.testing.assert_allclose(ab, _to_banded(a, l, u), rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(f_ps, a @ x_ps - b)

    def test_nonlinear(self):
        # F_p = x_p^3 + x_(p-1) - 2 x_(p+1)：対角 3 x_p^2、下 1、上 -2
        def f(x):
            r = x ** 3
            r[1:] += x[:-1]
            r[:-1] -= 2.0 * x[1:]
            return r

        n = 8
        x_ps = np.linspace(0.5, 2.0, n)
        _, ab = banded_jacobian(f, x_ps, l=1, u=1)
        expected = np.diag(3.0 * x_ps ** 2) + np.diag(np.ones(n - 1), -1) + np.diag(-2.0 * np.ones(n - 1), 1)
        np.testing.assert_allclose(ab, _to_banded(expected, 1, 1), rtol=1e-6, atol=1e-6)

    @pytest.mark.parametrize('l, u, n', [(1, 1, 33), (3, 3, 66)])
    def test_number_of_calls(self, l, u, n):
        # 残差を計算する回数は「帯の幅 + 1」（未知数の数によらない）
        calls = []
        a = _random_banded_matrix(n, l, u)

        def f(x):
            calls.append(1)
            return a @ x

        banded_jacobian(f, np.ones(n), l=l, u=u)
        assert len(calls) == l + u + 1 + 1
