# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

from typing import Tuple, Optional

from sensirion_driver_adapters.mocks.response_provider import (ResponseProvider,
                                                               RandomResponse)
from sensirion_driver_adapters.rx_tx_data import RxData
from sensirion_driver_adapters.shdlc_adapter.shdlc_channel import ShdlcTransceiver


class ShdlcTransceiverMock(ShdlcTransceiver):

    def __init__(self, sensor_mock,
                 response_provider: Optional[ResponseProvider] = None) -> None:
        self._sensor_mock = sensor_mock
        self._response_provider = response_provider or RandomResponse()
        self._expected_length = 0

    def set_expected_length(self, response: Optional[RxData]) -> None:
        if response is None:
            self._expected_length = 0
            return
        self._expected_length = response.rx_length

    def transceive(self, slave_address,
                   command_id,
                   data,
                   response_timeout) -> Tuple[int, int, int, bytes]:
        self._sensor_mock.write(command_id, data)
        return (slave_address, command_id,
                0,
                self._sensor_mock.read(command_id, self._expected_length))
