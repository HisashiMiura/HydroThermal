import pytest


from modules.materials import Materials


def test_load():

    ms = Materials()

    m = ms.get_material('シージング')

    assert m.lambda_h == 0.0586
    assert m.lambda_dsh_m == 2.61E-11
    assert m.c == 0.0
    assert m.rho == 0.0
    assert m.psi0 == 0.0

