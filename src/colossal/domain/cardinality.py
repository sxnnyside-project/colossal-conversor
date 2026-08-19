from enum import Enum


class ConversionCardinality(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

    def is_multi_output(self) -> bool:
        return self in (ConversionCardinality.ONE_TO_MANY, ConversionCardinality.MANY_TO_MANY)

    def is_multi_input(self) -> bool:
        return self in (ConversionCardinality.MANY_TO_ONE, ConversionCardinality.MANY_TO_MANY)
