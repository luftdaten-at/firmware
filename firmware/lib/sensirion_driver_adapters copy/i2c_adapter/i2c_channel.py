# -*- coding: utf-8 -*-
# (c) Copyright 2021 Sensirion AG, Switzerland

from sensirion_i2c_driver.crc_calculator import CrcCalculator
from sensirion_i2c_driver.errors import I2cChecksumError

from sensirion_driver_adapters.channel import TxRxChannel, TxRxRequest
from sensirion_driver_adapters.rx_tx_data import RxData


class I2cChannel(TxRxChannel):
    """This is the concrete channel implementation to be used with I2cConnection of the package
    sensirion-i2c-driver"""

    def __init__(self, connection, slave_address=0, crc=None) -> None:
        """Initialization of i2c channel.

        :param connection:
            The i2c connection that is used to communicate with the device.
        :param slave_address:
            The i2c slave address of the attached device.
        :param crc:
            The CrcCalculator that is used to compute the CRC. If crc is not provided, no checksums will be inserted.
        """
        self._connection = connection
        self._slave_address = slave_address
        self._crc = crc

    def write_read(self, tx_bytes,
                   payload_offset: int,
                   response,
                   device_busy_delay: float = 0.0,
                   post_processing_delay = None,
                   slave_address = None,
                   ignore_errors: bool = False):
        """Implementation of abstract write_read method."""

        tx_bytes = I2cChannel.build_tx_data(tx_bytes, payload_offset, self._crc)
        rx_len = None
        if response:
            rx_len = response.rx_length
            if self._crc:
                rx_len = 3 * rx_len // 2

        tx_rx = TxRxRequest(channel=self, response=response, tx_bytes=tx_bytes,
                            device_busy_delay=device_busy_delay,
                            post_processing_time=post_processing_delay,
                            receive_length=rx_len)
        if slave_address is None:
            slave_address = self._slave_address
        try:
            result = self._connection.execute(slave_address, tx_rx)
        except Exception as error:
            if not ignore_errors:
                raise error
            result = None
        return result

    def i2c_general_call_reset(self):
        """
        Issue a i2c reset by writing the byte 0x6 on the general call address.

        :Note:
            - all devices attached to this bus will be reset
            - after the reset, the channel blocks for 50ms to allow the devices to reboot.
        """
        self.write_read(tx_bytes=[0x6],
                        payload_offset=1,
                        response=None,
                        slave_address=0,
                        ignore_errors=True,
                        post_processing_delay=0.05
                        )

    @property
    def timeout(self):
        return 0.0

    def strip_protocol(self, data):
        """
        Validates the CRCs of the received data from the device and returns
        the data with all CRCs removed.

        :param bytes data:
            Received raw bytes from the read operation.
        :return:
            The received bytes without crc, or None if there is no data received.
        :rtype:
            bytes or None
        :raise ~sensirion_i2c_driver.errors.I2cChecksumError:
            If a received CRC was wrong.
        """
        if self._crc is None:
            return data  # data does not contain CRCs -> return it as-is

        data = bytearray(data)  # Python 2 compatibility
        return self.strip_and_check_crc(data, self._crc)

    @staticmethod
    def strip_and_check_crc(data: bytearray, crc: CrcCalculator):
        """
        Strip all crc's from the data

        With the i2c protocol a crc is inserted after every two bytes. This function removes the inserted CRC's and
        throws an exception if the checksum is not correct.

        :param data:
            The byte string including crc's.

        :param crc:
            The crc calculator that is used to compute the CRC

        :return:
            data without crc checksums.

        :raise ~sensirion_i2c_driver.errors.I2cChecksumError:
            If a received CRC was wrong.
        """
        data_without_crc = bytearray()
        for i in range(len(data)):
            if i % 3 == 2:
                received_crc = data[i]
                expected_crc = crc(data[i - 2:i])
                if received_crc != expected_crc:
                    raise I2cChecksumError(received_crc, expected_crc, data)
            else:
                data_without_crc.append(data[i])
        return bytes(data_without_crc) if len(data_without_crc) else None

    @staticmethod
    def build_tx_data(tx_data, cmd_width, crc):
        """
        Build the raw bytes to send from given command and TX data.

        :param cmd_width:
            This is the width of the command. Since CRC only starts after the command bytes we need to
            have this information
        :param tx_data:
            The byte array to be transmitting
        :param crc:
            A callable object that computes the crc from a bytes array.
        :return:
            The raw bytes to send, or None if no write header is needed.
        :rtype:
            bytearray/None
        """
        if not tx_data:
            return None

        data = bytearray(tx_data[:cmd_width])  # the command is in the beginning of the tx_data
        tx_data = bytearray(tx_data[cmd_width:] or [])  # Python 2 compatibility
        for i in range(len(tx_data)):
            data.append(tx_data[i])
            if (crc is not None) and (i % 2 == 1):
                data.append(crc(tx_data[i - 1:i + 1]))
        return bytes(data)
