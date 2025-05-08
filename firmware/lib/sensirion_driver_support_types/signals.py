# -*- coding: utf-8 -*-

class AbstractSignal():
    """Describes the protocol of any signal used within a driver.
    """

    @property
    def name(self) -> str:
        name: str = self.__class__.__name__
        label = 'Signal'
        label_len = len(label)
        i = name.index(label)
        if i > -1:
            if len(name) > i + label_len:
                return name[i + label_len:]
            return name[:i]
        return name

    @property
    def value(self) -> float:
        raise NotImplementedError()

    def __str__(self) -> str:
        raise NotImplementedError()


class ScaleAndOffsetSignal(AbstractSignal):

    def __init__(self,
                 raw_value,
                 scaling = 1.0,
                 offset = 0.0,
                 num_digits: int = 6,
                 num_decimals: int = 2) -> None:
        self._fmt = f'{{:{num_digits - num_decimals}.{num_decimals}f}}'
        self._value = (raw_value - offset) / scaling

    @property
    def number_format(self) -> str:
        return self._fmt

    @number_format.setter
    def number_format(self, value: str) -> None:
        self._fmt = value

    @property
    def value(self) -> float:
        return self._value

    def __str__(self) -> str:
        return self._fmt.format(self._value)
