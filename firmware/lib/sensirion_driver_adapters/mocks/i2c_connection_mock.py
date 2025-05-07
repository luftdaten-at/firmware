# -*- coding: utf-8 -*-
# (c) Copyright 2021 Sensirion AG, Switzerland

import adafruit_logging as logging
import time
from typing import Optional, Tuple, Any

from sensirion_driver_adapters.channel import TxRxRequest
from sensirion_driver_adapters.mocks.i2c_sensor_mock import I2cSensorMock

connection_logger = logging.getLogger(__name__)


class I2cConnectionMock:
    """
    An i2c connection is used within the i2c channel to communicate with a sensor. This mock provides the same
    interface to the channel when instantiated with a sensor_mock.
    """
    def __init__(self, sensor_mock: I2cSensorMock) -> None:
        self._connected_sensor = sensor_mock

    def execute(self, address: int, tx_rx: TxRxRequest) -> Optional[Tuple[Any]]:
        """
        Implement interface required by I2cChannel

        :param address:
            i2c slave address
        :param tx_rx:
            TxRxRequest object. The tx_rx is a container for the request and response data.
        :returns:
            A tuple containing the result of the request
        """
        if tx_rx.tx_data is not None:
            self._connected_sensor.write(address, tx_rx.tx_data)
            if tx_rx.read_delay > 0:
                time.sleep(tx_rx.read_delay)
        response = None
        # we should always try to read even if the length is 0
        expected_length = tx_rx.rx_length if tx_rx.rx_length is not None else 0
        data = self._connected_sensor.read(address, expected_length)
        if tx_rx.rx_length:
            response = tx_rx.interpret_response(data)
        if tx_rx.post_processing_time > 0:
            time.sleep(tx_rx.post_processing_time)
        return response
