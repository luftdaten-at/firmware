# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

import time
from typing import Optional, Tuple

from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection

from sensirion_driver_adapters.channel import TxRxChannel
from sensirion_driver_adapters.channel_provider import I2cChannelProvider
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel


class LinuxI2cChannelProvider(I2cChannelProvider):
    """Create a channel that is using a I2cConnection to communicate with a sensor over Linux i2c device."""

    def __init__(self, linux_device: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._linux_i2c_device = linux_device
        self._i2c_transceiver: Optional[LinuxI2cTransceiver] = None

    def release_channel_resources(self):
        """Free up all resources that where acquired when initializing the channel"""
        if self._i2c_transceiver is not None:
            self._i2c_transceiver.close()
        self._i2c_transceiver = None
        self._linux_i2c_device = None

    def prepare_channel(self):
        """Initialize a concrete channel object that operates on a Linux i2c device."""
        self._i2c_transceiver = LinuxI2cTransceiver(device_file=self._linux_i2c_device)
        time.sleep(0.1)

    def get_channel(self, slave_address: int,
                    crc_parameters: Optional[Tuple[int, int, int, int]]) -> TxRxChannel:
        """
        Create and return an initialized channel based on an Linux I2c device.

        The channel provider can return several channels with different channel parameters. This is needed in case
        more than one sensor is attached on the same bus.

        :param slave_address:
            The i2c address where the sensor is attached
        :param crc_parameters:
            The crc calculator that can compute the crc checksum of the byte stream
        """

        return I2cChannel(I2cConnection(self._i2c_transceiver),
                          slave_address=slave_address,
                          crc=self.try_create_crc_calculator(crc_parameters))
