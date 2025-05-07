# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

import abc
from typing import Optional, Tuple

from sensirion_i2c_driver import CrcCalculator

from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcChannel


class ChannelProvider(abc.ABC):
    """
    Base class for channel providers.

    The base class implements the context manager interface of a channel provider and provides the template
    methods to allocate and release channel resources.
    """

    def __enter__(self) -> "ChannelProvider":
        self.prepare_channel()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release_channel_resources()

    @abc.abstractmethod
    def release_channel_resources(self) -> None:
        """Free up all resources that where acquired when initializing the channel."""

    @abc.abstractmethod
    def prepare_channel(self) -> None:
        """Initialize a concrete programming device object that can be used to create a new channel instances."""


class I2cChannelProvider(ChannelProvider):
    """Provide an abstract interface that can be used to create channels for different purposes."""

    def __init__(self,
                 i2c_frequency: float = 100e3,
                 supply_voltage: float = 3.3) -> None:
        """
        Initialization of channel provider with defaults. Not all values are used by all channel providers.

        :param i2c_frequency:
            The i2c frequency that is applicable on the i2c bus
        :param supply_voltage:
            The supply voltage of the sensor
        """
        self.i2c_frequency = i2c_frequency
        self.supply_voltage = supply_voltage

    @staticmethod
    def try_create_crc_calculator(parameters: Optional[Tuple[int, int, int, int]]) -> Optional[CrcCalculator]:
        """Evaluate the CRC parameters. If not None, create a CrcCalculator instance. Otherwise, return None."""
        if parameters is None:
            return None
        return CrcCalculator(*parameters)

    @abc.abstractmethod
    def get_channel(self, slave_address: int,
                    crc_parameters: Optional[Tuple[int, int, int, int]]) -> I2cChannel:
        """
        Create and return an initialized channel to communicate with the sensor.

        The channel provider can return several channels with different channel parameters. This is needed in case
        more than one sensor is attached on the same bus.

        :param slave_address:
            The i2c address where the sensor is attached
        :param crc_parameters:
            The parameters that are required to compute he crc proper checksum of the byte stream. If the parameter is
            set to None, no crc will be computed.
        """


class ShdlcChannelProvider(ChannelProvider):
    """Provide an abstract interface that can be used to create shdlc channels for different purposes."""

    @abc.abstractmethod
    def get_channel(self, channel_delay: float) -> ShdlcChannel:
        """
        Create and return a SHDLC channel.

        :param channel_delay:
            Any roundtrip time below this channel delay will not cause a timeout exception.
        """
