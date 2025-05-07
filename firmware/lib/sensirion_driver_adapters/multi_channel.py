# -*- coding: utf-8 -*-
# (c) Copyright 2021 Sensirion AG, Switzerland

from typing import Tuple, Optional, Iterator, Any

from sensirion_driver_adapters.channel import TxRxChannel, AbstractMultiChannel


class MultiChannel(AbstractMultiChannel):

    def __init__(self, channels: Tuple[TxRxChannel]) -> None:
        super().__init__()
        self._channels = channels
        self._active_channel: Optional[TxRxChannel] = None
        self._channel_iterator: Optional[Iterator[TxRxChannel]] = None

    @property
    def channel_count(self) -> int:
        return len(self._channels)

    def get_channel(self, i: int) -> TxRxChannel:
        return self._channels[i]

    def __enter__(self) -> AbstractMultiChannel:
        self._channel_iterator = iter(self._channels)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._channel_iterator = None
        self._active_channel = None
        return exc_type is None

    def write_read(self, tx_bytes,
                   payload_offset,
                   response,
                   device_busy_delay=0.0,
                   post_processing_delay=None,
                   slave_address=None,
                   ignore_errors=False) -> Any:
        """
        Implementation of write read.

        Write read needs to be called in a open context (with statement block)
        """
        self._active_channel = next(self._channel_iterator)
        return self._active_channel.write_read(tx_bytes=tx_bytes,
                                               payload_offset=payload_offset,
                                               response=response,
                                               device_busy_delay=device_busy_delay,
                                               post_processing_delay=post_processing_delay,
                                               slave_address=slave_address,
                                               ignore_errors=ignore_errors)

    def strip_protocol(self, data) -> None:
        self._active_channel.strip_protocol(data)

    @property
    def timeout(self) -> float:
        # this function may be called outside a write_read 'transaction'
        if self._active_channel is not None:
            return self._active_channel.timeout
        return self._channels[0].timeout
