# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

import time
from typing import Optional, Tuple

from sensirion_i2c_driver import I2cConnection
from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
from sensirion_shdlc_sensorbridge import (SensorBridgePort,
                                          SensorBridgeShdlcDevice,
                                          SensorBridgeI2cProxy)

from sensirion_driver_adapters.channel import TxRxChannel
from sensirion_driver_adapters.channel_provider import I2cChannelProvider
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel


class SensorBridgeI2cChannelProvider(I2cChannelProvider):
    """Create a channel that is using a I2cConnection to communicate with a sensor over the SensorBridgeShdlcDevice."""

    def __init__(self, sensor_bridge_port: SensorBridgePort,
                 serial_port: str,
                 serial_baud_rate: int,
                 *args, **kwargs):
        """
        Initialize additional members for sensor bridge channel.

        :param sensor_bridge_port:
            The port of the sensor bridge where the sensor is attached
        :param serial_port:
            The serial port or serial device that is used by a programming device that uses the serial interface
        :param serial_baud_rate:
            The baud rate that can be applied on the serial line used by a programming device that uses the serial
            interface.
        """
        super().__init__(*args, **kwargs)
        self._sensor_bridge_port: SensorBridgePort = sensor_bridge_port
        self.serial_port = serial_port
        self.serial_baud_rate = serial_baud_rate
        self._shdlc_port: Optional[ShdlcSerialPort] = None
        self._sensor_bridge: Optional[SensorBridgeShdlcDevice] = None
        self._i2c_transceiver: Optional[SensorBridgeI2cProxy] = None

    def release_channel_resources(self):
        """
        Free up all resources that where acquired when initializing the channel:
            - switch off power
            - release serial connection
        """
        if self._sensor_bridge is None:
            return
        assert self._sensor_bridge_port is not None, "Illegal state: SensorBridgePort is None!"
        assert self._shdlc_port is not None, "Illegal state: Shdlc port is None!"
        self._sensor_bridge.switch_supply_off(self._sensor_bridge_port)
        self._shdlc_port.close()
        self._shdlc_port = None

    def prepare_channel(self):
        """Initialize a concrete channel object that can be used to create a new sensor instance."""
        self._shdlc_port = ShdlcSerialPort(port=self.serial_port, baudrate=self.serial_baud_rate)
        self._sensor_bridge = SensorBridgeShdlcDevice(connection=ShdlcConnection(self._shdlc_port),
                                                      slave_address=0)
        self._sensor_bridge.set_i2c_frequency(self._sensor_bridge_port, frequency=self.i2c_frequency)
        self._sensor_bridge.set_supply_voltage(self._sensor_bridge_port, voltage=self.supply_voltage)
        self._sensor_bridge.switch_supply_on(self._sensor_bridge_port)
        self._i2c_transceiver = SensorBridgeI2cProxy(self._sensor_bridge, port=self._sensor_bridge_port)
        time.sleep(0.1)

    def get_channel(self, slave_address: int,
                    crc_parameters: Tuple[int, int, int, int]) -> TxRxChannel:
        """
        Create and return an initialized channel based on an I2cConnection.

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
