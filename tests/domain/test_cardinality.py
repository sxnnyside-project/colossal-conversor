from __future__ import annotations

from colossal.domain.cardinality import ConversionCardinality


def test_cardinality_semantics() -> None:
    one_to_one = ConversionCardinality.ONE_TO_ONE
    one_to_many = ConversionCardinality.ONE_TO_MANY
    many_to_one = ConversionCardinality.MANY_TO_ONE
    many_to_many = ConversionCardinality.MANY_TO_MANY

    assert not one_to_one.is_multi_output()
    assert not one_to_one.is_multi_input()

    assert one_to_many.is_multi_output()
    assert not one_to_many.is_multi_input()

    assert not many_to_one.is_multi_output()
    assert many_to_one.is_multi_input()

    assert many_to_many.is_multi_output()
    assert many_to_many.is_multi_input()
