# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

import adafruit_logging as logging
from typing import Optional

from sensirion_driver_adapters.mocks.response_provider import ResponseProvider, RandomResponse

logger = logging.getLogger(__name__)


class ShdlcSensorMock:
    """The sensor mock provides a base functionalities for mocking any kind of sensor.

    The responsibilities of the SHDLC sensor mock are:
    - Provide a hook for returning specific data that can be checked by the receiver
    - Check the SHDLC slave address
    """

    def __init__(self,
                 response_provider: Optional[ResponseProvider],
                 mock_id: int = 0,
                 slave_address: int = 0) -> None:
        """
        Initialize mock specific arguments.

        :param response_provider:
            An object that can return sensor specific responses.
        :param mock_id:
            An identification to know which mock was used
        :param slave_address:
            the shdlc slave address, will be 0 in most cases
        """
        self.slave_address = slave_address
        self._id = mock_id
        self._request_queue = []
        self._response_provider = response_provider if response_provider is not None else RandomResponse()

    def update_channel_parameters(self, response_provider: Optional[ResponseProvider] = None) -> None:
        """Allow to switch the channel properties"""

        if response_provider is not None:
            self._response_provider = response_provider

    def write(self, cmd_id: int, data: bytes) -> None:
        self._request_queue.append((cmd_id, data))
        logger.info(f'device {self._response_provider.get_id()}-{self._id} received command {cmd_id}')

    def read(self, cmd_id: int, nr_of_bytes: int) -> bytes:
        # for shdlc we always have a preceding request
        cmd, data = self._request_queue.pop(0)
        assert cmd == cmd_id
        return self._response_provider.handle_command(cmd, data, nr_of_bytes)
