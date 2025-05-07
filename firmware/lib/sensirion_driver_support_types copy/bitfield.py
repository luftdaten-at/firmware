# -*- coding: utf-8 -*-
from typing import Any, NamedTuple

"""Allow to specify the offset and the width of a bitfield within an integer"""
BitField = NamedTuple('BitField', [('offset', int), ('width', int)])


class BitfieldContainer:
    """This class will be used as a mixin. The specializing class is expected to declare the
    used bitfields as class variables. see in the test bench for examples
    """
    def __init__(self, int_value: int = 0):
        self._int_value: int = int_value

    def __str__(self):
        field_values = []
        for item, value in self.__class__.__dict__.items():
            if isinstance(value, BitField):
                field_values.append(f'{item}: {hex(self._get_value(value))}')
        return f"{{{', '.join(field_values)}}}"

    def __int__(self):
        return self.value

    def __getattribute__(self, item: str) -> Any:
        attr = super().__getattribute__(item)
        if isinstance(attr, BitField):
            return self._get_value(attr)
        return attr

    def __setattr__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            attr = super().__getattribute__(key)
            if isinstance(attr, BitField):
                self._set_value(attr, value)
                return
        super().__setattr__(key, value)

    @staticmethod
    def _get_mask(width: int) -> int:
        return (1 << width) - 1

    def _get_value(self, bitfield: BitField) -> int:
        mask = self._get_mask(bitfield.width)
        return (self._int_value >> bitfield.offset) & mask

    def _set_value(self, bitfield: BitField, value: int) -> None:
        mask = self._get_mask(bitfield.width)
        self._int_value &= ~(mask << bitfield.offset)
        self._int_value |= ((value & mask) << bitfield.offset)

    @property
    def value(self) -> int:
        return self._int_value
