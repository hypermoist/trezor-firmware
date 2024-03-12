import ustruct
from micropython import const
from typing import TYPE_CHECKING
from storage.cache_thp import SessionThpCache
from trezor import io, loop, utils
from trezor.crypto import crc
from trezor.wire.protocol_common import Message
import trezor.wire.thp_session as THP
from trezor.wire.thp_session import (
    ThpError,
    SessionState,
    BROADCAST_CHANNEL_ID,
)
from ubinascii import hexlify

if TYPE_CHECKING:
    from trezorio import WireInterface

_MAX_PAYLOAD_LEN = const(60000)
_CHECKSUM_LENGTH = const(4)
_CHANNEL_ALLOCATION_REQ = 0x40
_CHANNEL_ALLOCATION_RES = 0x40
_ERROR = 0x41
_CONTINUATION_PACKET = 0x80
_ACK_MESSAGE = 0x20
_HANDSHAKE_INIT = 0x00
_PLAINTEXT = 0x01
ENCRYPTED_TRANSPORT = 0x02
_ENCODED_PROTOBUF_DEVICE_PROPERTIES = (
    b"\x0a\x04\x54\x33\x57\x31\x10\x05\x18\x00\x20\x01\x28\x01\x28\x02"
)
_UNALLOCATED_SESSION_ERROR = (
    b"\x55\x4e\x41\x4c\x4c\x4f\x43\x41\x54\x45\x44\x5f\x53\x45\x53\x53\x49\x4f\x4e"
)

_REPORT_LENGTH = const(64)
_REPORT_INIT_DATA_OFFSET = const(5)
_REPORT_CONT_DATA_OFFSET = const(3)


class InitHeader:
    format_str = ">BHH"

    def __init__(self, ctrl_byte, cid, length) -> None:
        self.ctrl_byte = ctrl_byte
        self.cid = cid
        self.length = length

    def to_bytes(self) -> bytes:
        return ustruct.pack(
            InitHeader.format_str, self.ctrl_byte, self.cid, self.length
        )

    def pack_to_buffer(self, buffer, buffer_offset=0) -> None:
        ustruct.pack_into(
            InitHeader.format_str,
            buffer,
            buffer_offset,
            self.ctrl_byte,
            self.cid,
            self.length,
        )

    def pack_to_cont_buffer(self, buffer, buffer_offset=0) -> None:
        ustruct.pack_into(">BH", buffer, buffer_offset, _CONTINUATION_PACKET, self.cid)


class InterruptingInitPacket:
    def __init__(self, report: bytes) -> None:
        self.initReport = report


async def read_message(iface: WireInterface, buffer: utils.BufferType) -> Message:
    msg = await read_message_or_init_packet(iface, buffer)
    while type(msg) is not Message:
        if isinstance(msg, InterruptingInitPacket):
            msg = await read_message_or_init_packet(iface, buffer, msg.initReport)
        else:
            raise ThpError("Unexpected output of read_message_or_init_packet:")
    return msg


async def read_message_or_init_packet(
    iface: WireInterface, buffer: utils.BufferType, firstReport: bytes | None = None
) -> Message | InterruptingInitPacket:
    report = firstReport
    while True:
        # Wait for an initial report
        if report is None:
            report = await _get_loop_wait_read(iface)
        if report is None:
            raise ThpError("Reading failed unexpectedly, report is None.")

        # Channel multiplexing
        ctrl_byte, cid = ustruct.unpack(">BH", report)

        if cid == BROADCAST_CHANNEL_ID:
            await _handle_broadcast(iface, ctrl_byte, report)  # TODO await
            report = None
            continue

        # We allow for only one message to be read simultaneously. We do not
        # support reading multiple messages with interleaven packets - with
        # the sole exception of cid_request which can be handled independently.
        if _is_ctrl_byte_continuation(ctrl_byte):
            # continuation packet is not expected - ignore
            report = None
            continue

        payload_length = ustruct.unpack(">H", report[3:])[0]
        payload = _get_buffer_for_payload(payload_length, buffer)
        header = InitHeader(ctrl_byte, cid, payload_length)

        # buffer the received data
        interruptingPacket = await _buffer_received_data(payload, header, iface, report)
        if interruptingPacket is not None:
            return interruptingPacket

        # Check CRC
        if not _is_checksum_valid(payload[-4:], header.to_bytes() + payload[:-4]):
            # checksum is not valid -> ignore message
            report = None
            continue

        session = THP.get_session(iface, cid)
        session_state = THP.get_state(session)

        # Handle message on unallocated channel
        if session_state == SessionState.UNALLOCATED:
            message = await _handle_unallocated(iface, cid)
            # unallocated should not return regular message, TODO, but it might change
            if message is not None:
                return message
            report = None
            continue

        if session is None:
            raise ThpError("Invalid session!")

        # Note: In the Host, the UNALLOCATED_CHANNEL error should be handled here

        # Synchronization process
        sync_bit = (ctrl_byte & 0x10) >> 4

        # 1: Handle ACKs
        if _is_ctrl_byte_ack(ctrl_byte):
            _handle_received_ACK(session, sync_bit)
            report = None
            continue

        # 2: Handle message with unexpected synchronization bit
        if sync_bit != THP.sync_get_receive_expected_bit(session):
            message = await _handle_unexpected_sync_bit(iface, cid, sync_bit)
            # unsynchronized messages should not return regular message, TODO,
            # but it might change with the cancelation message
            if message is not None:
                return message
            report = None
            continue

        # 3: Send ACK in response
        await _sendAck(iface, cid, sync_bit)
        THP.sync_set_receive_expected_bit(session, 1 - sync_bit)

        return await _handle_allocated(ctrl_byte, session, payload)


def _get_loop_wait_read(iface: WireInterface):
    return loop.wait(iface.iface_num() | io.POLL_READ)


def _get_buffer_for_payload(
    payload_length: int, existing_buffer: utils.BufferType
) -> utils.BufferType:
    if payload_length > _MAX_PAYLOAD_LEN:
        raise ThpError("Message too large")
    if payload_length > len(existing_buffer):
        # allocate a new buffer to fit the message
        try:
            payload: utils.BufferType = bytearray(payload_length)
        except MemoryError:
            payload = bytearray(_REPORT_LENGTH)
            raise ThpError("Message too large")
        return payload

    # reuse a part of the supplied buffer
    return memoryview(existing_buffer)[:payload_length]


async def _buffer_received_data(
    payload: utils.BufferType, header: InitHeader, iface, report
) -> None | InterruptingInitPacket:
    # buffer the initial data
    nread = utils.memcpy(payload, 0, report, _REPORT_INIT_DATA_OFFSET)
    while nread < header.length:
        # wait for continuation report
        report = await _get_loop_wait_read(iface)

        # channel multiplexing
        cont_ctrl_byte, cont_cid = ustruct.unpack(">BH", report)

        # handle broadcast - allows the reading process
        # to survive interruption by broadcast
        if cont_cid == BROADCAST_CHANNEL_ID:
            await _handle_broadcast(iface, cont_ctrl_byte, report)
            continue

        # handle unexpected initiation packet
        if not _is_ctrl_byte_continuation(cont_ctrl_byte):
            # TODO possibly add timeout - allow interruption only after a long time
            return InterruptingInitPacket(report)

        # ignore continuation packets on different channels
        if cont_cid != header.cid:
            continue

        # buffer the continuation data
        nread += utils.memcpy(payload, nread, report, _REPORT_CONT_DATA_OFFSET)


async def write_message(
    iface: WireInterface, message: Message, is_retransmission: bool = False
) -> None:
    session = THP.get_session_from_id(message.session_id)
    if session is None:
        raise ThpError("Invalid session")

    cid = THP.get_cid(session)
    payload = message.type.to_bytes(2, "big") + message.data
    payload_length = len(payload)

    if THP.get_state(session) == SessionState.INITIALIZED:
        # write message in plaintext, TODO check if it is allowed
        ctrl_byte = _PLAINTEXT
    elif THP.get_state(session) == SessionState.APP_TRAFFIC:
        ctrl_byte = ENCRYPTED_TRANSPORT
    else:
        raise ThpError("Session in not implemented state" + str(THP.get_state(session)))

    if not is_retransmission:
        ctrl_byte = _add_sync_bit_to_ctrl_byte(
            ctrl_byte, THP.sync_get_send_bit(session)
        )
        THP.sync_set_send_bit_to_opposite(session)
    else:
        # retransmission must have the same sync bit as the previously sent message
        ctrl_byte = _add_sync_bit_to_ctrl_byte(
            ctrl_byte, 1 - THP.sync_get_send_bit(session)
        )

    header = InitHeader(ctrl_byte, cid, payload_length + _CHECKSUM_LENGTH)
    checksum = _compute_checksum_bytes(header.to_bytes() + payload)
    await write_to_wire(iface, header, payload + checksum)
    # TODO set timeout for retransmission


async def write_to_wire(
    iface: WireInterface, header: InitHeader, payload: bytes
) -> None:
    loop_write = loop.wait(iface.iface_num() | io.POLL_WRITE)

    payload_length = len(payload)

    # prepare the report buffer with header data
    report = bytearray(_REPORT_LENGTH)
    header.pack_to_buffer(report)

    # write initial report
    nwritten = utils.memcpy(report, _REPORT_INIT_DATA_OFFSET, payload, 0)
    await _write_report(loop_write, iface, report)

    # if we have more data to write, use continuation reports for it
    if nwritten < payload_length:
        header.pack_to_cont_buffer(report)

    while nwritten < payload_length:
        nwritten += utils.memcpy(report, _REPORT_CONT_DATA_OFFSET, payload, nwritten)
        await _write_report(loop_write, iface, report)


async def _write_report(write, iface: WireInterface, report: bytearray) -> None:
    while True:
        await write
        n = iface.write(report)
        if n == len(report):
            return


async def _handle_broadcast(iface: WireInterface, ctrl_byte, report) -> Message | None:
    if ctrl_byte != _CHANNEL_ALLOCATION_REQ:
        raise ThpError("Unexpected ctrl_byte in broadcast channel packet")
    length, nonce, checksum = ustruct.unpack(">H8s4s", report[3:])

    if not _is_checksum_valid(checksum, data=report[:-4]):
        raise ThpError("Checksum is not valid")

    channel_id = _get_new_channel_id()
    THP.create_new_unauthenticated_session(iface, channel_id)
    response_data = (
        ustruct.pack(">8sH", nonce, channel_id) + _ENCODED_PROTOBUF_DEVICE_PROPERTIES
    )

    response_header = InitHeader(
        _CHANNEL_ALLOCATION_RES,
        BROADCAST_CHANNEL_ID,
        len(response_data) + _CHECKSUM_LENGTH,
    )

    checksum = _compute_checksum_bytes(response_header.to_bytes() + response_data)
    await write_to_wire(iface, response_header, response_data + checksum)


async def _handle_allocated(ctrl_byte, session: SessionThpCache, payload) -> Message:
    # Parameters session and ctrl_byte will be used to determine if the
    # communication should be encrypted or not

    message_type = ustruct.unpack(">H", payload)[0]

    # trim message type and checksum from payload
    message_data = payload[2:-_CHECKSUM_LENGTH]
    return Message(message_type, message_data, session.session_id)


def _handle_received_ACK(session: SessionThpCache, sync_bit: int) -> None:
    # No ACKs expected
    if THP.sync_can_send_message(session):
        return

    # ACK has incorrect sync bit
    if THP.sync_get_send_bit(session) != sync_bit:
        return

    # ACK is expected and it has correct sync bit
    THP.sync_set_can_send_message(session, True)


async def _handle_unallocated(iface, cid) -> Message | None:
    data = _UNALLOCATED_SESSION_ERROR
    header = InitHeader(_ERROR, cid, len(data) + _CHECKSUM_LENGTH)
    checksum = _compute_checksum_bytes(header.to_bytes() + data)
    await write_to_wire(iface, header, data + checksum)


async def _sendAck(iface: WireInterface, cid: int, ack_bit: int) -> None:
    ctrl_byte = _add_sync_bit_to_ctrl_byte(_ACK_MESSAGE, ack_bit)
    header = InitHeader(ctrl_byte, cid, _CHECKSUM_LENGTH)
    checksum = _compute_checksum_bytes(header.to_bytes())
    await write_to_wire(iface, header, checksum)


async def _handle_unexpected_sync_bit(
    iface: WireInterface, cid: int, sync_bit: int
) -> Message | None:
    await _sendAck(iface, cid, sync_bit)

    # TODO handle cancelation messages and messages on allocated channels without synchronization
    # (some such messages might be handled in the classical "allocated" way, if the sync bit is right)


def _get_new_channel_id() -> int:
    return THP.get_next_channel_id()


def _is_checksum_valid(checksum: bytes | utils.BufferType, data: bytes) -> bool:
    data_checksum = _compute_checksum_bytes(data)
    return checksum == data_checksum


def _is_ctrl_byte_continuation(ctrl_byte) -> bool:
    return ctrl_byte & 0x80 == _CONTINUATION_PACKET


def _is_ctrl_byte_ack(ctrl_byte) -> bool:
    return ctrl_byte & 0x20 == _ACK_MESSAGE


def _add_sync_bit_to_ctrl_byte(ctrl_byte, sync_bit):
    if sync_bit == 0:
        return ctrl_byte & 0xEF
    if sync_bit == 1:
        return ctrl_byte | 0x10
    raise ThpError("Unexpected synchronization bit")


def _compute_checksum_bytes(data: bytes | utils.BufferType):
    return crc.crc32(data).to_bytes(4, "big")