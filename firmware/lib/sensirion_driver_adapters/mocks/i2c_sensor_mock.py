# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

import adafruit_logging as logging
import struct
from typing import Optional

from sensirion_i2c_driver.crc_calculator import CrcCalculator

from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_driver_adapters.mocks.response_provider import ResponseProvider, RandomResponse

logger = logging.getLogger(__name__)


class I2cSensorMock:
    """The sensor mock provides a base functionalities for mocking any kind of sensor.

    The responsibilities of the sensor mock are:
    - Check proper address
    - Check proper encoding of data stream. This includes the CRC check on reception and the
      encoding of returned data
    - Provide a hook for returning specific data that can be checked by the receiver
    """

    def __init__(self,
                 response_provider: Optional[ResponseProvider],
                 cmd_width: int = 2,
                 mock_id: int = 0,
                 i2c_address: Optional[int] = None,
                 crc: Optional[CrcCalculator] = None) -> None:
        """
        Initialize mock specific arguments.

        :param response_provider:
            An object that can return sensor specific responses.
        :param cmd_width:
            Nr of bytes used by one command_id
        :param mock_id:
            An identification to know which mock was used
        :param i2c_address:
            i2c address of the mocked sensor; may be initialized by the channel provider

        """
        self._cmd_width = cmd_width
        self._crc: Optional[CrcCalculator] = crc
        self.i2c_address: Optional[int] = i2c_address
        self._id = mock_id
        self._request_queue = []
        self._response_provider = response_provider if response_provider is not None else RandomResponse()
        self._last_command: Optional[int] = None

    def update_channel_parameters(self, slave_address,
                                  crc: Optional[CrcCalculator],
                                  cmd_width: Optional[int] = None,
                                  response_provider: Optional[ResponseProvider] = None) -> None:
        """Allow to switch the channel properties"""
        self._crc = crc
        self.i2c_address = slave_address
        if cmd_width is not None:
            self._cmd_width = cmd_width
        if response_provider is not None:
            self._response_provider = response_provider

    def write(self, _: int, data: bytes) -> None:
        # in case we have a wake-up command, we may send only one byte of data
        cmd_len = min(len(data), self._cmd_width)
        self._last_command = struct.unpack(self.command_template(cmd_len), data[:cmd_len])[0]
        if self._crc is not None:
            data = I2cChannel.strip_and_check_crc(bytearray(data[cmd_len:]), self._crc)
        self._request_queue.append((self._last_command, data))
        logger.info(f'device {self._response_provider.get_id()}-{self._id} received command {self._last_command}')

    def read(self, address, nr_of_bytes_to_return) -> bytes:
        cmd, data = self._last_command, bytes()
        if any(self._request_queue):
            # we may read data without a preceding request!
            cmd, data = self._request_queue.pop(0)
        assert address == 0 or address == self.i2c_address, "unsupported i2c address"
        if nr_of_bytes_to_return <= 0:
            # we should get a chance to react on commands in the mock even though we do not return data
            return self._response_provider.handle_command(cmd, data, 0)
        nr_of_bytes = 2 * nr_of_bytes_to_return // 3
        logger.info(f'device {self._response_provider.get_id()}-{self._id} received'
                    f'read request for {nr_of_bytes} bytes')

        rx_data = self._response_provider.handle_command(cmd, data, nr_of_bytes)
        if self._crc is None:
            return rx_data
        return I2cChannel.build_tx_data(rx_data, 0, self._crc)

    @staticmethod
    def command_template(cmd_width) -> str:
        return '>H' if cmd_width == 2 else '>B'
