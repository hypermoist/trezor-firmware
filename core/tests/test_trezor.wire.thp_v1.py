from common import *
from ubinascii import hexlify, unhexlify
import ustruct

from trezor import io, utils
from trezor.loop import wait
from trezor.utils import chunks
from trezor.wire import thp_v1
from trezor.wire.thp_v1 import _CHECKSUM_LENGTH, BROADCAST_CHANNEL_ID
from trezor.wire.protocol_common import Message
import trezor.wire.thp_session as THP

from micropython import const


class MockHID:
    def __init__(self, num):
        self.num = num
        self.data = []

    def iface_num(self):
        return self.num

    def write(self, msg):
        self.data.append(bytearray(msg))
        return len(msg)

    def wait_object(self, mode):
        return wait(mode | self.num)


MESSAGE_TYPE = 0x4242
MESSAGE_TYPE_BYTES = b"\x42\x42"
_MESSAGE_TYPE_LEN = 2
PLAINTEXT_0 = 0x01
PLAINTEXT_1 = 0x11
COMMON_CID = 4660
CONT = 0x80

HEADER_INIT_LENGTH = 5
HEADER_CONT_LENGTH = 3
INIT_MESSAGE_DATA_LENGTH = (
    thp_v1._REPORT_LENGTH - HEADER_INIT_LENGTH - _MESSAGE_TYPE_LEN
)


def make_header(ctrl_byte, cid, length):
    return ustruct.pack(">BHH", ctrl_byte, cid, length)


def make_cont_header():
    return ustruct.pack(">BH", CONT, COMMON_CID)


def makeSimpleMessage(header, message_type, message_data):
    return header + ustruct.pack(">H", message_type) + message_data


def makeCidRequest(header, message_data):
    return header + message_data


def printBytes(a):
    print(hexlify(a).decode("utf-8"))


def getPlaintext() -> bytes:
    if THP.sync_get_receive_expected_bit(THP.get_active_session()) == 1:
        return PLAINTEXT_1
    PLAINTEXT_0


def getCid() -> int:
    return THP.get_cid(THP.get_active_session())


# This test suite is an adaptation of test_trezor.wire.codec_v1
class TestWireTrezorHostProtocolV1(unittest.TestCase):
    def setUp(self):
        self.interface = MockHID(0xDEADBEEF)
        if not utils.USE_THP:
            import storage.cache_thp  # noQA:F401

    def test_simple(self):
        cid_req_header = make_header(
            ctrl_byte=0x40, cid=BROADCAST_CHANNEL_ID, length=12
        )
        cid_request_dummy_data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x96\x64\x3c\x6c"
        cid_req_message = makeCidRequest(cid_req_header, cid_request_dummy_data)

        message_header = make_header(ctrl_byte=0x01, cid=COMMON_CID, length=18)
        cid_request_dummy_data_checksum = b"\x67\x8e\xac\xe0"
        message = makeSimpleMessage(
            message_header,
            MESSAGE_TYPE,
            cid_request_dummy_data + cid_request_dummy_data_checksum,
        )

        buffer = bytearray(64)

        gen = thp_v1.read_message(self.interface, buffer)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))

        with self.assertRaises(StopIteration) as e:
            gen.send(cid_req_message)
            gen.send(message)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, cid_request_dummy_data)

        buffer_without_zeroes = buffer[: len(message) - 5]
        message_without_header = message[5:]
        # message should have been read into the buffer
        self.assertEqual(buffer_without_zeroes, message_without_header)

    def test_read_one_packet(self):
        # zero length message - just a header
        PLAINTEXT = getPlaintext()
        header = make_header(
            PLAINTEXT, cid=COMMON_CID, length=_MESSAGE_TYPE_LEN + _CHECKSUM_LENGTH
        )
        checksum = thp_v1._compute_checksum_bytes(header + MESSAGE_TYPE_BYTES)
        message = header + MESSAGE_TYPE_BYTES + checksum

        buffer = bytearray(64)
        gen = thp_v1.read_message(self.interface, buffer)

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))

        with self.assertRaises(StopIteration) as e:
            gen.send(message)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, b"")

        # message should have been read into the buffer
        self.assertEqual(buffer, MESSAGE_TYPE_BYTES + checksum + b"\x00" * 58)

    def test_read_many_packets(self):
        message = bytes(range(256))
        header = make_header(
            getPlaintext(),
            COMMON_CID,
            len(message) + _MESSAGE_TYPE_LEN + _CHECKSUM_LENGTH,
        )
        checksum = thp_v1._compute_checksum_bytes(header + MESSAGE_TYPE_BYTES + message)
        # message = MESSAGE_TYPE_BYTES + message + checksum

        # first packet is init header + 59 bytes of data
        # other packets are cont header + 61 bytes of data
        cont_header = make_cont_header()
        packets = [header + MESSAGE_TYPE_BYTES + message[:INIT_MESSAGE_DATA_LENGTH]] + [
            cont_header + chunk
            for chunk in chunks(
                message[INIT_MESSAGE_DATA_LENGTH:] + checksum,
                64 - HEADER_CONT_LENGTH,
            )
        ]
        buffer = bytearray(262)
        gen = thp_v1.read_message(self.interface, buffer)
        query = gen.send(None)
        for packet in packets[:-1]:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = gen.send(packet)

        # last packet will stop
        with self.assertRaises(StopIteration) as e:
            gen.send(packets[-1])

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value

        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message)

        # message should have been read into the buffer )
        self.assertEqual(buffer, MESSAGE_TYPE_BYTES + message + checksum)

    def test_read_large_message(self):
        message = b"hello world"
        header = make_header(
            getPlaintext(),
            COMMON_CID,
            _MESSAGE_TYPE_LEN + len(message) + _CHECKSUM_LENGTH,
        )

        packet = (
            header
            + MESSAGE_TYPE_BYTES
            + message
            + thp_v1._compute_checksum_bytes(header + MESSAGE_TYPE_BYTES + message)
        )

        # make sure we fit into one packet, to make this easier
        self.assertTrue(len(packet) <= thp_v1._REPORT_LENGTH)

        buffer = bytearray(1)
        self.assertTrue(len(buffer) <= len(packet))

        gen = thp_v1.read_message(self.interface, buffer)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        with self.assertRaises(StopIteration) as e:
            gen.send(packet)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message)

        # read should have allocated its own buffer and not touch ours
        self.assertEqual(buffer, b"\x00")

    def test_write_one_packet(self):
        message = Message(MESSAGE_TYPE, b"", THP._get_id(self.interface, COMMON_CID))
        gen = thp_v1.write_message(self.interface, message)

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_WRITE))
        with self.assertRaises(StopIteration):
            gen.send(None)

        header = make_header(
            PLAINTEXT_0, COMMON_CID, _MESSAGE_TYPE_LEN + _CHECKSUM_LENGTH
        )
        expected_message = (
            header
            + MESSAGE_TYPE_BYTES
            + thp_v1._compute_checksum_bytes(header + MESSAGE_TYPE_BYTES)
            + b"\x00" * (INIT_MESSAGE_DATA_LENGTH - _CHECKSUM_LENGTH)
        )
        self.assertTrue(self.interface.data == [expected_message])

    def test_write_multiple_packets(self):
        message_payload = bytes(range(256))
        message = Message(
            MESSAGE_TYPE, message_payload, THP._get_id(self.interface, COMMON_CID)
        )
        gen = thp_v1.write_message(self.interface, message)

        header = make_header(
            PLAINTEXT_1,
            COMMON_CID,
            len(message.data) + _MESSAGE_TYPE_LEN + _CHECKSUM_LENGTH,
        )
        cont_header = make_cont_header()
        checksum = thp_v1._compute_checksum_bytes(
            header + message.type.to_bytes(2, "big") + message.data
        )
        packets = [
            header + MESSAGE_TYPE_BYTES + message.data[:INIT_MESSAGE_DATA_LENGTH]
        ] + [
            cont_header + chunk
            for chunk in chunks(
                message.data[INIT_MESSAGE_DATA_LENGTH:] + checksum,
                thp_v1._REPORT_LENGTH - HEADER_CONT_LENGTH,
            )
        ]

        for _ in packets:
            # we receive as many queries as there are packets
            query = gen.send(None)
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_WRITE))

        # the first sent None only started the generator. the len(packets)-th None
        # will finish writing and raise StopIteration
        with self.assertRaises(StopIteration):
            gen.send(None)

        # packets must be identical up to the last one
        self.assertListEqual(packets[:-1], self.interface.data[:-1])
        # last packet must be identical up to message length. remaining bytes in
        # the 64-byte packets are garbage -- in particular, it's the bytes of the
        # previous packet
        last_packet = packets[-1] + packets[-2][len(packets[-1]) :]
        self.assertEqual(last_packet, self.interface.data[-1])

    def test_roundtrip(self):
        message_payload = bytes(range(256))
        message = Message(
            MESSAGE_TYPE, message_payload, THP._get_id(self.interface, COMMON_CID)
        )
        gen = thp_v1.write_message(self.interface, message)

        # exhaust the iterator:
        # (XXX we can only do this because the iterator is only accepting None and returns None)
        for query in gen:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_WRITE))

        buffer = bytearray(1024)
        gen = thp_v1.read_message(self.interface, buffer)
        query = gen.send(None)
        for packet in self.interface.data[:-1]:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = gen.send(packet)

        with self.assertRaises(StopIteration) as e:
            gen.send(self.interface.data[-1])

        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message.data)

    def test_read_huge_packet(self):
        PACKET_COUNT = 1180
        # message that takes up 1 180 USB packets
        message_size = (PACKET_COUNT - 1) * (
            thp_v1._REPORT_LENGTH
            - HEADER_CONT_LENGTH
            - _CHECKSUM_LENGTH
            - _MESSAGE_TYPE_LEN
        ) + INIT_MESSAGE_DATA_LENGTH

        # ensure that a message this big won't fit into memory
        # Note: this control is changed, because THP has only 2 byte length field
        self.assertTrue(message_size > thp_v1._MAX_PAYLOAD_LEN)
        # self.assertRaises(MemoryError, bytearray, message_size)
        header = make_header(PLAINTEXT_1, COMMON_CID, message_size)
        packet = header + MESSAGE_TYPE_BYTES + (b"\x00" * INIT_MESSAGE_DATA_LENGTH)
        buffer = bytearray(65536)
        gen = thp_v1.read_message(self.interface, buffer)

        query = gen.send(None)

        # THP returns "Message too large" error after reading the message size,
        # it is different from codec_v1 as it does not allow big enough messages
        # to raise MemoryError in this test
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        with self.assertRaises(thp_v1.ThpError) as e:
            query = gen.send(packet)

        self.assertEqual(e.value.args[0], "Message too large")


if __name__ == "__main__":
    unittest.main()