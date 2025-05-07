# -*- coding: utf-8 -*-
# (c) Copyright 2022 Sensirion AG, Switzerland


from enum import IntFlag
from typing import Iterable, Optional
from typing import List

from sensirion_i2c_driver import I2cConnection, CrcCalculator
from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
from sensirion_shdlc_sensorbridge import (SensorBridgePort,
                                          SensorBridgeShdlcDevice,
                                          SensorBridgeI2cProxy)

from sensirion_driver_adapters.channel import AbstractMultiChannel
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_driver_adapters.multi_channel import MultiChannel


class UsedPorts(IntFlag):
    """Flag to indicate which ports being used."""
    PORT_1 = 1
    PORT_2 = 2
    ALL = 3


class Config:
    """Holds the configuration of a single attached SensorBridge device.

    :param serial_port: Serial port used by a SensorBridge device.
    :param ports: SensorBridge port(s) used to communicate with the desired sensor(s).
    """
    def __init__(self, serial_port: str, ports: UsedPorts) -> None:
        self.serial_port: str = serial_port
        self.selected_ports: UsedPorts = ports


class SensorBridgeLiveInfo:
    def __init__(self, sensor_bridge: SensorBridgeShdlcDevice, ports: Optional[List[SensorBridgePort]]) -> None:
        self.sensor_bridge = sensor_bridge
        self.ports: List[SensorBridgePort] = ports if ports is not None else list()


class I2cMultiSensorBridgeConnection:
    """
    The class I2cMultiSensorBridgeConnection is a convenience method to support the creation of a multi-channel
    object for one or several SensorBridges devices.

    The multi-channel object with N channels can be used to communicate simultaneously with N different sensors
    :param config_list: List of configuration objects.
    :param baud_rate: Uart speed to be used for the multi-channel. The same baud rate will be used with all SensorBridge
        devices.
    :param i2c_frequency: The I2c frequency used for communication with the sensors.
    :param voltage: The supply voltage used by the attached sensors.
    """
    def __init__(self, config_list: Iterable[Config], baud_rate: int, i2c_frequency: int, voltage: float) -> None:
        self._config_list = config_list
        self._baud_rate = baud_rate
        self._i2c_frequency = i2c_frequency
        self._voltage = voltage
        self._serial_ports: List[ShdlcSerialPort] = []
        self._proxies: List[SensorBridgeI2cProxy] = []
        self._sensor_bridges: List[SensorBridgeLiveInfo] = []

    def _create_proxies(self, serial: ShdlcSerialPort, selected_ports: UsedPorts) -> None:
        bridge = SensorBridgeShdlcDevice(ShdlcConnection(serial), slave_address=0)

        sensor_bridge_port_list = [SensorBridgePort(i) for i in range(2) if selected_ports.value & (1 << i) != 0]
        # we need this information in order to power off an on the different channels later on!
        self._sensor_bridges.append(SensorBridgeLiveInfo(sensor_bridge=bridge, ports=sensor_bridge_port_list))
        for sensor_bridge_port in sensor_bridge_port_list:
            bridge.set_i2c_frequency(sensor_bridge_port, self._i2c_frequency)
            bridge.set_supply_voltage(sensor_bridge_port, self._voltage)
            bridge.switch_supply_on(sensor_bridge_port)
            self._proxies.append(SensorBridgeI2cProxy(bridge, sensor_bridge_port))

    def __enter__(self) -> "I2cMultiSensorBridgeConnection":
        for config in self._config_list:
            serial = ShdlcSerialPort(port=config.serial_port, baudrate=self._baud_rate)
            self._serial_ports.append(serial)
            self._create_proxies(serial, config.selected_ports)
        return self

    def get_multi_channel(self, i2c_address, crc: CrcCalculator) -> AbstractMultiChannel:
        """Create a multi-channel object for the configured SensorBridge devices and selected SensorBridge ports.
        """
        assert len(self._proxies) > 0, "Wrong usage: proxies not initialized"
        channels = tuple([I2cChannel(I2cConnection(x), i2c_address, crc) for x in self._proxies])
        return MultiChannel(channels)

    def switch_supply_off(self):
        """ Switch the supply off for all connected sensors."""
        for bridge_live in self._sensor_bridges:
            for port in bridge_live.ports:
                bridge_live.sensor_bridge.switch_supply_off(port)

    def switch_supply_on(self):
        """ Switch the supply on for all connected sensors."""
        for bridge_live in self._sensor_bridges:
            for port in bridge_live.ports:
                bridge_live.sensor_bridge.switch_supply_on(port)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.switch_supply_off()
        [port.close() for port in self._serial_ports]
        self._serial_ports.clear()
        return False
