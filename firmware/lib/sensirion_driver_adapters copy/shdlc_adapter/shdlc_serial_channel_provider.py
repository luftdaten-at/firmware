# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

from typing import Optional

from sensirion_shdlc_driver.port import ShdlcSerialPort

from sensirion_driver_adapters.channel_provider import ShdlcChannelProvider
from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcPortWrapper, ShdlcChannel


class ShdlcSerialPortChannelProvider(ShdlcChannelProvider):
    """Create a channel that is using a I2cConnection to communicate with a sensor over the SensorBridgeShdlcDevice."""

    def __init__(self, serial_port: str,
                 serial_baud_rate: int):
        """
        Initialize additional members for shdlc channel.

        :param serial_port:
            The serial port or serial device that is used by a programming device that uses the serial interface
        :param serial_baud_rate:
            The baud rate that can be applied on the serial line used by a programming device that uses the serial
            interface.
        """
        super().__init__()
        self.serial_port = serial_port
        self.serial_baud_rate = serial_baud_rate
        self._shdlc_port: Optional[ShdlcSerialPort] = None

    def release_channel_resources(self):
        """
        Free up all resources that where acquired when initializing the channel:
            - release serial connection
        """
        if self._shdlc_port is None:
            return
        self._shdlc_port.close()
        self._shdlc_port = None

    def prepare_channel(self):
        """Initialize a concrete channel object that can be used to create a new sensor instance."""
        self._shdlc_port = ShdlcSerialPort(port=self.serial_port, baudrate=self.serial_baud_rate)

    def get_channel(self, channel_delay: float) -> ShdlcChannel:
        """
        Create and return an initialized channel based on an ShdlcSerialPort.

        The channel provider can return several channels with different channel parameters. This is needed in case
        more than one sensor is attached on the same bus.


        """
        assert self._shdlc_port is not None, "Port not initialized!"
        return ShdlcChannel(ShdlcPortWrapper(self._shdlc_port), channel_delay=channel_delay)
