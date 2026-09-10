import numpy as np

from scripts.analog_path.data_layer import state_c_from_path


def test_state_c_endpoints_are_zero():
    A = np.array([0.0, -0.001, 0.002, -0.0005, 0.001, 0.0007, -0.002,
                  0.0003, -0.001, 0.0015, -0.0008, 0.002, -0.001, 0.004])
    C = state_c_from_path(A)
    assert C[0] == 0.0
    assert C[-1] == 0.0
    assert len(C) == 14


def test_state_c_is_path_minus_linear_ramp():
    A = np.array([0.0, -0.001, 0.002, -0.0005, 0.001, 0.0007, -0.002,
                  0.0003, -0.001, 0.0015, -0.0008, 0.002, -0.001, 0.004])
    ramp = np.arange(14, dtype=float) / 13.0 * A[13]
    assert np.allclose(state_c_from_path(A), A - ramp, atol=1e-15)


def test_state_c_removes_endpoint_magnitude():
    # same shape, different endpoint drift -> identical C
    A1 = np.array([0.0, 0.001, 0.000, 0.002, 0.001, 0.003, 0.002,
                   0.001, 0.002, 0.000, 0.001, 0.002, 0.001, 0.003])
    A2 = A1 + np.arange(14, dtype=float) / 13.0 * 0.010  # +1% linear drift
    assert np.allclose(state_c_from_path(A1), state_c_from_path(A2), atol=1e-15)


def test_state_c_constant_rate_path_is_zero():
    A = np.arange(14, dtype=float) / 13.0 * (-0.006)
    assert np.allclose(state_c_from_path(A), 0.0, atol=1e-15)


def test_state_c_nan_propagation():
    A = np.array([0.0, np.nan] + [0.0] * 12)
    C = state_c_from_path(A)
    assert np.isnan(C).sum() >= 1
