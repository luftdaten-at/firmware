# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

from typing import Optional, Tuple

from sensirion_driver_adapters.channel import TxRxChannel
from sensirion_driver_adapters.mocks.response_provider import ResponseProvider
from sensirion_driver_adapters.channel_provider import I2cChannelProvider
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_driver_adapters.mocks.i2c_connection_mock import I2cConnectionMock
from sensirion_driver_adapters.mocks.i2c_sensor_mock import I2cSensorMock


class MockI2cChannelProvider(I2cChannelProvider):
    """
    Create an i2c mock channel. This channel does not need hardware and can be used for testing.
    """

    def __init__(self,
                 command_width: int,
                 response_provider: Optional[ResponseProvider] = None,
                 mock_id: int = 0,
                 *args, **kwargs) -> None:
        """
        :param command_width:
            Nr of bytes that are used by the command
        :param response_provider:
            A class that generates a response for a given command and parameters
        :param mock_id:
            A number that identifies the mock - used in logs.
        """
        super().__init__(*args, **kwargs)

        self._sensor_mock = I2cSensorMock(cmd_width=command_width, response_provider=response_provider, mock_id=mock_id)

    def release_channel_resources(self):
        """Free up all resources that where acquired when initializing the channel. Nothing to be done."""
        ...

    def prepare_channel(self):
        """Initialize a concrete channel object that can be used to create a new sensor instance."""
        ...

    def get_channel(self, slave_address: int,
                    crc_parameters: Optional[Tuple[int, int, int, int]],
                    response_provider: Optional[ResponseProvider] = None) -> TxRxChannel:
        """Return the initialized channel."""

        crc = self.try_create_crc_calculator(crc_parameters)
        self._sensor_mock.update_channel_parameters(slave_address=slave_address,
                                                    crc=crc,
                                                    response_provider=response_provider)
        connection_mock = I2cConnectionMock(self._sensor_mock)
        return I2cChannel(connection=connection_mock,
                          slave_address=slave_address,
                          crc=crc)

    @property
    def sensor_mock(self):
        return self._sensor_mock
