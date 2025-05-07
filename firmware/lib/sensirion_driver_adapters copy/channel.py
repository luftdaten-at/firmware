# -*- coding: utf-8 -*-
# (c) Copyright 2021 Sensirion AG, Switzerland

from sensirion_driver_adapters.rx_tx_data import RxData


class TxRxChannel():
    """
    This is the abstract base class for any channel. A channel is a transportation medium to transfer data from any
    source to any destination.
    """

    def write_read(self, tx_bytes, payload_offset: int,
                   response: RxData,
                   device_busy_delay: float = 0.0,
                   post_processing_delay = None,
                   slave_address = None,
                   ignore_errors = False): 
        """
        Transfers the data to and from sensor.

        :param tx_bytes:
            Raw bytes to be transmitted
        :param payload_offset:
            The data my contain a header that needs to be left untouched, pushing the date through the protocol stack.
            The Payload offset points to the end of the header and the beginning of the data
        :param response:
            The response is an object that is able to unpack a raw response.
            It has to provide a method 'interpret_response.
        :param device_busy_delay:
            Indication how long the receiver of the message will be busy until processing of the data has been
            completed.
            Time unit: seconds
        :param post_processing_delay:
            This is the time one has to wait for until the next communication with the device can take place.
            Time unit: seconds
        :param slave_address:
            Used for i2c addressing. Denotes the i2c address of the receiving slave
        :param ignore_errors:
            Some transfers may generate an exception even when they execute properly. In these situations the exception
            is swallowed and an empty result is returned
        :return:
            Return a tuple of the interpreted data or None if there is no response at all
        """
        pass

    def strip_protocol(self, data) -> None:
        """"""
        pass

    @property
    def timeout(self) -> float:
        pass


class AbstractMultiChannel(TxRxChannel):
    """
    This is the base class for any multi channel implementation. A multi channel is used to mimic simultaneous
    communication with several sensors and is used by the MultiDeviceDecorator.
    """

    @property
    def channel_count(self) -> int:
        """return: number of contained channels"""
        raise NotImplementedError()

    def get_channel(self, i: int) -> TxRxChannel:
        """
        Return a specific channel.

        The returned channel my work properly only during the transaction (within the
        with .. block). The exact behaviour is up to the the AbstractMultiChannel implementation.
        """
        raise NotImplementedError()

    def __enter__(self) -> "AbstractMultiChannel":
        """
        A MultiChannel is a context manager. The begin and end of the communication over the contained channels is
        marked by the __enter__ and __exit__ method.
        """
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Marks the end of the communication over contained channels."""
        raise NotImplementedError()


class TxRxRequest:
    """This class is an adapter to the class I2cConnection. It keeps compatibility with the SensirionI2cCommand"""

    def __init__(self, channel,
                 tx_bytes=None,
                 response=None,
                 device_busy_delay=0.0,
                 post_processing_time=0.0,
                 receive_length=0) -> None:
        self._channel = channel
        self._response = response
        self._tx_data = tx_bytes
        self._device_busy_delay = device_busy_delay
        self._rx_length = receive_length
        self._post_processing_time = post_processing_time

    @property
    def read_delay(self):
        return self._device_busy_delay

    @property
    def tx_data(self):
        return self._tx_data

    @property
    def rx_length(self):
        return self._rx_length

    @property
    def timeout(self):
        return self._channel.timeout

    @property
    def post_processing_time(self):
        """This is the time that has to be waited before the next communication with the sensor can take place.
        """
        if self._post_processing_time is not None:
            return self._post_processing_time
        if self._response is None:
            return self.read_delay
        return 0.0

    def interpret_response(self, data):
        raw_data = self._channel.strip_protocol(data)
        if self._response is not None:
            return self._response.unpack(raw_data)
        return None
