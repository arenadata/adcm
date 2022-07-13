from collections.abc import Mapping


def get_default_constraint():
    return [0, '+']


def get_default_from_edition():
    return ['community']


def get_default_before_upgrade() -> dict:
    """Return init value for before upgrade"""
    return {'state': None}


def deep_merge(origin: dict, renovator: Mapping):
    """
    Merge renovator into origin

    >>> o = {'a': 1, 'b': {'c': 1, 'd': 1}}
    >>> r = {'a': 1, 'b': {'c': 2 }}
    >>> deep_merge(o, r) == {'a': 1, 'b': {'c': 2, 'd': 1}}
    """

    for key, value in renovator.items():
        if isinstance(value, Mapping):
            node = origin.setdefault(key, {})
            deep_merge(node, value)
        else:
            origin[key] = value
    return origin
