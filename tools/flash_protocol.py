"""Strict protobuf codec for the recovered Boufbowl client wire contract.

64-bit identities use decimal strings at JSON boundaries. No runtime decompiler
or third-party protobuf dependency is needed. XGaming authentication is excluded.
"""
import json
import math
from pathlib import Path
import struct

CONTRACT = Path(__file__).resolve().parent.parent / "protocol/client_contract.json"
MAX_PAYLOAD = 128 * 1024


class ProtocolError(ValueError):
    pass


def varint(value):
    if not 0 <= value < 1 << 64:
        raise ProtocolError("Varint outside uint64 range")
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def read_varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ProtocolError("Truncated varint")
        byte = data[offset]
        offset += 1
        if shift == 63 and byte > 1:
            raise ProtocolError("Varint exceeds uint64")
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ProtocolError("Overlong varint")


class Codec:
    def __init__(self, contract=CONTRACT, envelope_type="BoufbowlMessage"):
        self.envelope_type = envelope_type
        self.contract = json.loads(Path(contract).read_text())
        self.messages = self.contract["messages"]
        self.network = self.contract["network"]
        self.by_id = {spec["id"]: name for name, spec in self.network.items()}

    def schema(self, name):
        if name not in self.messages:
            raise ProtocolError(f"Unsupported message schema: {name}")
        return self.messages[name]["fields"]

    def encode(self, name, value, depth=0):
        if depth > 64 or not isinstance(value, dict):
            raise ProtocolError(f"{name}: expected object within depth limit")
        fields = self.schema(name)
        unknown = value.keys() - {f["name"] for f in fields}
        if unknown:
            raise ProtocolError(f"{name}: unknown fields {sorted(unknown)}")
        output = bytearray()
        for field in fields:
            key = field["name"]
            if key not in value:
                if field["required"]:
                    raise ProtocolError(f"{name}.{key}: required field missing")
                continue
            items = value[key] if field["repeated"] else [value[key]]
            if not isinstance(items, list):
                raise ProtocolError(f"{name}.{key}: expected array")
            for item in items:
                wire, payload = self.encode_value(field, item, depth)
                output.extend(varint(field["tag"] << 3 | wire))
                output.extend(payload)
        if len(output) > MAX_PAYLOAD:
            raise ProtocolError("Message exceeds client frame limit")
        return bytes(output)

    def encode_value(self, field, value, depth):
        kind = field["scalar"]
        if kind in ("MESSAGE", "STRING"):
            if kind == "MESSAGE":
                payload = self.encode(field["message"], value, depth + 1)
            else:
                if not isinstance(value, str):
                    raise ProtocolError(f"{field['name']}: expected string")
                payload = value.encode("utf-8")
            return 2, varint(len(payload)) + payload
        if kind == "DOUBLE":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ProtocolError(f"{field['name']}: expected number")
            if not math.isfinite(value):
                raise ProtocolError("Nonfinite double")
            return 1, struct.pack("<d", value)
        if kind == "BOOL":
            if not isinstance(value, bool):
                raise ProtocolError(f"{field['name']}: expected boolean")
            return 0, varint(int(value))
        if kind in ("INT64", "UINT64") and isinstance(value, str):
            try:
                integer = int(value)
            except ValueError as error:
                raise ProtocolError("Invalid decimal identity") from error
            if str(integer) != value:
                raise ProtocolError("Identity must be a canonical decimal string")
            value = integer
        if not isinstance(value, int) or isinstance(value, bool):
            raise ProtocolError(f"{field['name']}: expected integer")
        bits = 64 if kind.endswith("64") else 32
        signed = kind in ("INT32", "INT64", "SINT32", "ENUM")
        minimum, maximum = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)
        if not minimum <= value <= maximum:
            raise ProtocolError(f"{field['name']}: {kind} out of range")
        if kind == "SINT32":
            value = (value << 1) ^ (value >> 31)
        elif value < 0:
            value += 1 << 64
        return 0, varint(value)

    def decode(self, name, data, depth=0):
        if depth > 64 or len(data) > MAX_PAYLOAD:
            raise ProtocolError("Message exceeds size/depth limit")
        fields = {f["tag"]: f for f in self.schema(name)}
        value = {f["name"]: [] for f in fields.values() if f["repeated"]}
        offset = 0
        while offset < len(data):
            tag, offset = read_varint(data, offset)
            number, wire = tag >> 3, tag & 7
            if number == 0:
                raise ProtocolError("Invalid protobuf field zero")
            field = fields.get(number)
            raw, offset = self.read_value(data, offset, wire)
            if field is None:
                continue  # Original generated reader skips unknown fields.
            expected = 2 if field["scalar"] in ("STRING", "MESSAGE") else 1 if field["scalar"] == "DOUBLE" else 0
            if wire != expected:
                if field["repeated"] and expected == 0 and wire == 2:
                    packed_offset = 0
                    while packed_offset < len(raw):
                        item, packed_offset = read_varint(raw, packed_offset)
                        value[field["name"]].append(self.decode_value(field, item, depth))
                    continue
                raise ProtocolError(f"{name}.{field['name']}: incorrect wire type")
            item = self.decode_value(field, raw, depth)
            key = field["name"]
            if field["repeated"]:
                value[key].append(item)
            elif key in value:
                raise ProtocolError(f"{name}.{key}: duplicate singular field")
            else:
                value[key] = item
        missing = [f["name"] for f in fields.values() if f["required"] and f["name"] not in value]
        if missing:
            raise ProtocolError(f"{name}: missing required fields {missing}")
        return value

    @staticmethod
    def read_value(data, offset, wire):
        if wire == 0:
            return read_varint(data, offset)
        if wire == 2:
            length, offset = read_varint(data, offset)
        elif wire in (1, 5):
            length = 8 if wire == 1 else 4
        else:
            raise ProtocolError(f"Unsupported protobuf wire type: {wire}")
        if offset + length > len(data):
            raise ProtocolError("Truncated protobuf field")
        return data[offset:offset + length], offset + length

    def decode_value(self, field, raw, depth):
        kind = field["scalar"]
        if kind == "MESSAGE":
            return self.decode(field["message"], raw, depth + 1)
        if kind == "STRING":
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ProtocolError("Invalid UTF-8") from error
        if kind == "DOUBLE":
            value = struct.unpack("<d", raw)[0]
            if not math.isfinite(value):
                raise ProtocolError("Nonfinite double")
            return value
        if kind == "BOOL":
            if raw not in (0, 1):
                raise ProtocolError("Invalid boolean")
            return bool(raw)
        if kind == "SINT32":
            if raw >= 1 << 32:
                raise ProtocolError("SINT32 overflow")
            return (raw >> 1) ^ -(raw & 1)
        if kind in ("INT32", "ENUM"):
            raw &= (1 << 32) - 1
            return raw - (1 << 32) if raw >= 1 << 31 else raw
        if kind == "UINT32" and raw >= 1 << 32:
            raise ProtocolError("UINT32 overflow")
        if kind == "INT64":
            return str(raw - (1 << 64) if raw >= 1 << 63 else raw)
        if kind == "UINT64":
            return str(raw)
        return raw

    def envelope(self, name, payload):
        if name not in self.network:
            raise ProtocolError(f"Unsupported client message type: {name}")
        spec = self.network[name]
        return self.encode(self.envelope_type, {"type": spec["id"], spec["payload"]: payload})

    def open_envelope(self, data):
        envelope = self.decode(self.envelope_type, data)
        if envelope["type"] not in self.by_id:
            raise ProtocolError("Unsupported envelope discriminator")
        name = self.by_id[envelope["type"]]
        payload = self.network[name]["payload"]
        if set(envelope) != {"type", payload}:
            raise ProtocolError("Envelope must contain exactly its discriminator's payload")
        return {"type": name, "payload": envelope[payload]}


def frame(data):
    if not 0 < len(data) <= MAX_PAYLOAD:
        raise ProtocolError("Invalid frame length")
    return struct.pack(">I", len(data)) + data


class FrameDecoder:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        messages = []
        while len(self.buffer) >= 4:
            length = struct.unpack(">I", self.buffer[:4])[0]
            if not 0 < length <= MAX_PAYLOAD:
                raise ProtocolError("Invalid frame length")
            if len(self.buffer) < length + 4:
                break
            messages.append(bytes(self.buffer[4:length + 4]))
            del self.buffer[:length + 4]
        return messages
