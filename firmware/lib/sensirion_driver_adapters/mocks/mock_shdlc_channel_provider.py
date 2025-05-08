# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

from typing import Optional

from sensirion_driver_adapters.channel_provider import ShdlcChannelProvider
from sensirion_driver_adapters.mocks.response_provider import ResponseProvider
from sensirion_driver_adapters.mocks.shdlc_sensor_mock import ShdlcSensorMock
from sensirion_driver_adapters.mocks.shdlc_transceiver_mock import ShdlcTransceiverMock
from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcChannel


class ShdlcMockPortChannelProvider(ShdlcChannelProvider):
    """Create a channel that is using a I2cConnection to communicate with a sensor over the SensorBridgeShdlcDevice."""

    def __init__(self, response_provider: Optional[ResponseProvider] = None):
        """
        Initialize additional members for shdlc channel.

        :param response_provider:
            The response provider will return a response for a specific request.
        """
        super().__init__()
        self.sensor_mock = ShdlcSensorMock(response_provider)

    def get_id(self) -> int:
        return self._id

    def release_channel_resources(self):
        """Nothing needs to be done"""

    def prepare_channel(self):
        """Nothing needs to be done"""

    def get_channel(self, _: float = 0.1, response_provider: Optional[ResponseProvider] = None) -> ShdlcChannel:
        """
        Create and return an initialized SHDLC channel.

        The channel provider can return several channels with different channel parameters. This is needed in case
        more than one sensor is attached on the same bus.

        """
        self.sensor_mock.update_channel_parameters(response_provider=response_provider)
        return ShdlcChannel(ShdlcTransceiverMock(self.sensor_mock))
