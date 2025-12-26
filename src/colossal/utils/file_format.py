def to_snake_case(name: str) -> str:
    """Convert a CamelCase string to snake_case."""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def to_lower_case(name: str) -> str:
    """Convert a string to lower_case."""
    return name.lower()