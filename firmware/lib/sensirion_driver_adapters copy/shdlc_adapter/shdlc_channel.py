# -*- coding: utf-8 -*-
# (c) Copyright 2021 Sensirion AG, Switzerland
import abc
import adafruit_logging as logging
import struct
import time
from typing import Any, Iterable, Optional, Tuple, Union

from sensirion_shdlc_driver.errors import ShdlcDeviceError, ShdlcResponseError
from sensirion_shdlc_driver.port import ShdlcPort

from sensirion_driver_adapters.channel import TxRxChannel
from sensirion_driver_adapters.rx_tx_data import RxData

log = logging.getLogger(__name__)


class ShdlcTransceiver(abc.ABC):
    """Base class for any shdlc transceiver"""

    def transceive(self, slave_address,
                   command_id,
                   data,
                   response_timeout) -> Tuple[int, int, int, bytes]:
        """Call underlying transceive

        :param slave_address:
            shdlc slave_address
        :param command_id:
            SHDLC command that is sent
        :param data:
            the payload that is sent, this includes the subcommand.
        :param response_timeout:
            maximal time the roundtrip is allowed to take
        """

    def set_expected_length(self, response: Optional[RxData]) -> None:
        """
        Allows to compute the expected length.
        """


class ShdlcPortWrapper(ShdlcTransceiver):
    def __init__(self, port: ShdlcPort):
        self._port = port

    def transceive(self, slave_address, command_id, data, response_timeout) -> Tuple[int, int, int, bytes]:
        return self._port.transceive(slave_address=slave_address,
                                     command_id=command_id,
                                     data=data,
                                     response_timeout=response_timeout)

    def set_expected_length(self, _: Optional[RxData]) -> None:
        ...


class ShdlcChannel(TxRxChannel):

    def __init__(self, transceiver: Union[ShdlcTransceiver, ShdlcPort],
                 channel_delay: float = 0.05, shdlc_address: int = 0) -> None:

        # needed for backwards compatibility
        self._port: ShdlcTransceiver = self._make_transceiver(transceiver)
        self._channel_delay = channel_delay
        self._address = shdlc_address

    def write_read(self, tx_bytes: Iterable, payload_offset: int,
                   response: RxData,
                   device_busy_delay: float = 0.0,
                   post_processing_delay: Optional[float] = None,
                   slave_address: Optional[int] = None,
                   ignore_errors: bool = False) -> Optional[Tuple[Any, ...]]:
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
        :param post_processing_delay:
            This is the time one has to wait for until the next communication with the device can take place.
        :param slave_address:
            Used for shdlc address
        :param ignore_errors:
            Some transfers may generate an exception even when they execute properly. In these situations the exception
            is swallowed and an empty result is returned
        :return:
            Return a tuple of the interpreted data or None if there is no response at all
        """
        shdlc_address = slave_address or self._address
        cmd_id = struct.unpack('>B', tx_bytes[0:payload_offset])[0]
        data = tx_bytes[payload_offset:]
        timeout = max(self._channel_delay, device_busy_delay)
        self._port.set_expected_length(response)
        rx_addr, rx_cmd, rx_state, rx_data = self._port.transceive(slave_address=shdlc_address,
                                                                   command_id=cmd_id,
                                                                   data=data,
                                                                   response_timeout=timeout)
        if rx_addr != shdlc_address:
            raise ShdlcResponseError("Received slave address {} instead of {}."
                                     .format(rx_addr, shdlc_address))
        if rx_cmd != cmd_id:
            raise ShdlcResponseError("Received command ID 0x{:02X} instead of "
                                     "0x{:02X}.".format(rx_cmd, cmd_id))
        error_state = True if rx_state & 0x80 else False
        if error_state:
            log.warning("SHDLC device with address {} is in error state."
                        .format(shdlc_address))
        error_code = rx_state & 0x7F
        if error_code:
            log.warning("SHDLC device with address {} returned error {}."
                        .format(shdlc_address, error_code))
            raise ShdlcDeviceError(error_code)  # Command failed to execute
        if response:
            # The size of strings (and arrays?) is not known before receiving the response. The indications
            # in the rx descriptor are only the upper bounds. Therefore, each field is unpacked individually
            # and the position in the result frame is computed online.
            rx_data = response.unpack_dynamic_sized(rx_data)
        if post_processing_delay is not None:
            time.sleep(post_processing_delay)
        return rx_data

    def strip_protocol(self, data) -> None:
        """The protocol is already stripped by the connection"""
        return data

    @property
    def timeout(self) -> float:
        return self._channel_delay

    @staticmethod
    def _make_transceiver(transceiver: Union[ShdlcTransceiver, ShdlcPort]) -> ShdlcTransceiver:
        if isinstance(transceiver, ShdlcTransceiver):
            return transceiver
        return ShdlcPortWrapper(transceiver)
