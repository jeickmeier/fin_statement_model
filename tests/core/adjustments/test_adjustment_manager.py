import math

import pytest
from hypothesis import given, settings
from hypothesis.strategies import floats

from fin_statement_model.core.errors import AdjustmentError
from fin_statement_model.core.graph.domain.adjustment import Adjustment, AdjustmentType
from fin_statement_model.core.graph.services.adjustments import AdjustmentService


@pytest.mark.parametrize(
    "base, value, scale",
    [(-100.0, 2.0, 0.5)],
)
def test_negative_base_fractional_scale_returns_unchanged(
    base: float, value: float, scale: float
) -> None:
    """Ensure negative bases with fractional scales are ignored and *flag* is False."""
    adj = Adjustment(
        node="TestNode",
        period="2023",
        value=value,
        type=AdjustmentType.MULTIPLICATIVE,
        scale=scale,
        reason="unit-test",
    )
    manager = AdjustmentService()

    result, flag = manager.apply_adjustments(base, [adj])

    assert result == base
    assert flag is False


def test_huge_exponent_returns_base() -> None:
    """Ensure extremely large exponents do not overflow and simply return base."""
    base = 100.0
    adj = Adjustment(
        node="TestNode",
        period="2023",
        value=1e308,
        type=AdjustmentType.MULTIPLICATIVE,
        scale=1.0,
        reason="unit-test",
    )

    manager = AdjustmentService()
    result, flag = manager.apply_adjustments(base, [adj])

    assert result == base
    assert flag is False


def test_strict_mode_raises_on_invalid() -> None:
    """When *strict* is enabled invalid combos must raise AdjustmentError."""
    base = -50.0
    adj = Adjustment(
        node="TestNode",
        period="2023",
        value=2.0,
        type=AdjustmentType.MULTIPLICATIVE,
        scale=0.25,
        reason="strict-mode-test",
    )
    manager = AdjustmentService(strict=True)

    with pytest.raises(AdjustmentError):
        _ = manager.apply_adjustments(base, [adj])


@given(
    base=floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    value=floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False),
    scale=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=1000, deadline=300)
def test_fuzz_multiplicative_does_not_return_complex(
    base: float, value: float, scale: float
) -> None:
    """Fuzz test: *apply_adjustments* never returns complex numbers or NaN for a wide range of inputs."""
    adj = Adjustment(
        node="TestNode",
        period="2023",
        value=value,
        type=AdjustmentType.MULTIPLICATIVE,
        scale=scale,
        reason="fuzz",
    )
    manager = AdjustmentService()

    result, _ = manager.apply_adjustments(base, [adj])

    # Ensure the result is a real finite float
    assert not isinstance(result, complex)
    assert math.isfinite(result)
