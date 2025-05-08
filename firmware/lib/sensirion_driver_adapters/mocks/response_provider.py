# -*- coding: utf-8 -*-
# (c) Copyright 2023 Sensirion AG, Switzerland

import abc
import random


def random_bytes(data_length: int) -> bytes:
    """Compute a random data byte array of specified length"""
    return bytes(random.randint(0, 255) for _ in range(data_length))


def random_ascii_string(data_length: int) -> bytes:
    """Compute a random ascii string data response."""
    return bytes(random.randint(32, 126) for _ in range(data_length))


def padded_ascii_string(string_value: str, nr_of_characters: int) -> bytes:
    """
    Pad an ascii-string with 0 to match the expected response length.

    :param string_value:
        The string value that needs to be padded
    :param nr_of_characters:
        The final length that is required
    :returns:
        The prepared string buffer content.
    """
    return string_value.encode('ascii') + bytes([0] * (nr_of_characters - len(string_value)))


class ResponseProvider(abc.ABC):
    """Abstract base class that allows to inject arbitrary responses into a sensor mock.
    """

    @abc.abstractmethod
    def get_id(self) -> str:
        """Return an identifier of the response provider"""

    @abc.abstractmethod
    def handle_command(self, cmd_id: int, data: bytes, response_length: int) -> bytes:
        """
        Provide a hook for sensor specific command handling.

        With specific implementation of this class, it becomes possible to emulate any sensor.

        :param cmd_id:
            Command id of the command to emulate
        :param data:
            The parameters of the command. At this point the data do not contain a crc anymore
        :param response_length:
            The expected length of the returned bytes array

        :return:
            An emulated response.
        """


class RandomResponse(ResponseProvider):
    """Generates for any request a random byte sequence of specified length.
    """

    def get_id(self) -> str:
        return "random_default"

    def handle_command(self, cmd_id: int, data: bytes, response_length: int) -> bytes:
        if response_length <= 0:
            return bytes()
        return random_bytes(response_length)
