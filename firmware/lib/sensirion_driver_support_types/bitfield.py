# -*- coding: utf-8 -*-
# CircuitPython: no ``typing`` module — use ``collections.namedtuple`` for BitField.
from collections import namedtuple

"""Allow to specify the offset and the width of a bitfield within an integer"""
BitField = namedtuple("BitField", ("offset", "width"))


class BitfieldContainer:
    """This class will be used as a mixin. The specializing class is expected to declare the
    used bitfields as class variables. see in the test bench for examples
    """

    def __init__(self, int_value=0):
        self._int_value = int_value

    def __str__(self):
        field_values = []
        for item, value in self.__class__.__dict__.items():
            if isinstance(value, BitField):
                field_values.append(f"{item}: {hex(self._get_value(value))}")
        return f"{{{', '.join(field_values)}}}"

    def __int__(self):
        return self.value

    def __getattribute__(self, item):
        attr = super().__getattribute__(item)
        if isinstance(attr, BitField):
            return self._get_value(attr)
        return attr

    def __setattr__(self, key, value):
        if hasattr(self, key):
            attr = super().__getattribute__(key)
            if isinstance(attr, BitField):
                self._set_value(attr, value)
                return
        super().__setattr__(key, value)

    @staticmethod
    def _get_mask(width):
        return (1 << width) - 1

    def _get_value(self, bitfield):
        mask = self._get_mask(bitfield.width)
        return (self._int_value >> bitfield.offset) & mask

    def _set_value(self, bitfield, value):
        mask = self._get_mask(bitfield.width)
        self._int_value &= ~(mask << bitfield.offset)
        self._int_value |= ((value & mask) << bitfield.offset)

    @property
    def value(self):
        return self._int_value
