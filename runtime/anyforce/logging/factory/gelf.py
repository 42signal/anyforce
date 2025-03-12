import math
import random
import socket
import struct
from typing import Any

chunk_size = 1420
chunked_header_en = 12
chunked_data_len = chunk_size - chunked_header_en


class UDP:
    def __init__(self, address: str | tuple[str, int]) -> None:
        host, port = address.split(":") if isinstance(address, str) else address
        self.address = (host, int(port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def __getstate__(self) -> str:
        host, port = self.address
        return ":".join((host, str(port)))

    def __setstate__(self, state: Any) -> None:
        self.address = state

    def __deepcopy__(self, memodict: dict[str, object]):
        new_self = self.__class__(self.address)
        return new_self

    def __repr__(self) -> str:
        return f"<GelfUDP(address={self.address!r})>"

    def msg(self, message: bytes):
        total_chunks = self.calculate_chunk_number(message)
        if total_chunks <= 1:
            self.socket.sendto(message, self.address)
            return

        assert total_chunks <= 128
        message_id = random.randint(0, 0xFFFFFFFFFFFFFFFF)
        for sequence, chunk in enumerate(
            (
                message[i : i + chunked_data_len]
                for i in range(0, len(message), chunked_data_len)
            )
        ):
            self.socket.sendto(
                b"".join(
                    [
                        b"\x1e\x0f",
                        struct.pack("Q", message_id),
                        struct.pack("B", sequence),
                        struct.pack("B", total_chunks),
                        chunk,
                    ],
                ),
                self.address,
            )

    @staticmethod
    def calculate_chunk_number(message: bytes):
        return int(math.ceil(len(message) * 1.0 / chunked_data_len))

    log = debug = info = warn = warning = msg
    fatal = failure = err = error = critical = exception = msg


class UDPFactory:
    def __init__(self, address: str):
        self.address = address

    def __call__(self, *args: Any):
        return UDP(self.address)
