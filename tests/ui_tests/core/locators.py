from dataclasses import dataclass
from enum import Flag, auto
from operator import methodcaller
from typing import Type


class Descriptor(Flag):
    # locator is for internal use (e.g. element of list)
    SERVICE = auto()
    # locator should be available as element
    ELEMENT = auto()
    TEXT = auto()
    BUTTON = auto()
    INPUT = auto()


@dataclass()
class BaseLocator:
    by: str
    value: str
    name: str

    def __repr__(self):
        return self.name


class Locator(BaseLocator):
    flags: Descriptor = Descriptor.TEXT

    def __init__(self, by: str, value: str, flags: Descriptor = Descriptor.TEXT, name: str = ""):
        super().__init__(by=by, value=value, name=name)
        self.flags = flags


@dataclass
class TemplateLocator(Locator):
    """
    Similar to Locator, but with template in `value`
    and ability to generate Locators from template
    """

    def __call__(self, *args) -> Locator:
        """Get regular Locator by passing arguments to format function"""
        return Locator(by=self.by, value=self.value.format(*args), name=self.name.format(*args), flags=self.flags)


def autoname(cls: Type):
    class_prefix = (
        " ".join(
            map(_into_words, filter(lambda name: name not in ("Locator", "Locators"), cls.__qualname__.split(".")))
        )
        .strip()
        .capitalize()
    )
    unnamed = filter(
        lambda i: isinstance(i[1], Locator) and i[1].name == "",
        map(lambda attr: (attr, getattr(cls, attr)), dir(cls)),
    )
    for attr, locator in unnamed:
        locator.name = f"{class_prefix} {attr.replace('_', ' ')}"
        if Descriptor.BUTTON in locator.flags:
            locator.name += " button"
    return cls


def _into_words(word):
    result = word
    for upper_char in set(filter(methodcaller("isupper"), word)):
        result = result.replace(upper_char, f" {upper_char.lower()}")
    return result
