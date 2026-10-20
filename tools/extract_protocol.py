#!/usr/bin/env python3
"""Recover a reviewable wire contract from the original generated AS3 serializers."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT.parent / "migration-work/scripts/scripts/com/ankamagames/boufbowl"


def extract_message(path):
    text = path.read_text()
    if "implements IExternalizable" not in text:
        return None
    declarations = dict(re.findall(r"(?:public|private) var (\w+):(\w+)", text))
    getters = dict(re.findall(r"function get (\w+)\(\)\s*:\s*(\w+)", text))
    write = text.split("function writeExternal", 1)[1].split("function readExternal", 1)[0]
    read = text.split("function readExternal", 1)[1]
    cases = dict(re.findall(r"case (\d+):\s*(.*?)(?=case \d+:|default:)", read, re.S))
    fields = []
    tags = list(re.finditer(r"WriteUtils\.writeTag\(param1,WireType\.(\w+),(\d+)\);", write))
    for index, tag in enumerate(tags):
        chunk = write[tag.end():tags[index + 1].start() if index + 1 < len(tags) else len(write)]
        value = re.search(r"WriteUtils\.write_TYPE_(\w+)\(param1,this\.(\w+)", chunk)
        if not value:
            raise ValueError(f"Unsupported serializer at {path}:{tag.group(2)}")
        scalar, name = value.groups()
        field_type = declarations.get(name, getters.get(name))
        repeated = field_type == "Array"
        message = None
        if scalar == "MESSAGE":
            if repeated:
                constructors = re.findall(r"new (\w+)\(", cases[tag.group(2)])
                constructors = [c for c in constructors if c != "IOError"]
                if len(constructors) != 1:
                    raise ValueError(f"Ambiguous nested type: {path}:{name}: {constructors}")
                message = constructors[0]
            else:
                message = field_type
            if not message:
                raise ValueError(f"Missing nested type: {path}:{name}")
        optional = f"has{name[0].upper()}{name[1:]}" in getters
        fields.append({"name": name, "tag": int(tag.group(2)), "wire": tag.group(1),
                       "scalar": scalar, "message": message, "repeated": repeated,
                       "required": not repeated and not optional})
    return {"source": str(path.relative_to(REFERENCE)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "fields": fields}


def extract(reference):
    global REFERENCE
    REFERENCE = Path(reference).resolve()
    protocol = REFERENCE / "protocol"
    messages = {}
    enums = {}
    for path in sorted(protocol.rglob("*.as")):
        message = extract_message(path)
        if message is not None:
            messages[path.stem] = message
        else:
            values = dict((name, int(number)) for name, number in re.findall(
                r"public static const (\w+):(?:int|uint) = (-?\d+);", path.read_text()))
            if values:
                enums[str(path.relative_to(protocol).with_suffix(""))] = values
    union = (protocol / "UnionProtocol.as").read_text().split("public function", 2)[-1]
    # The first getField switch is the authoritative discriminator/payload map.
    payloads = dict(re.findall(r"case Type\.(\w+):\s*return param1\.(\w+);", union))
    outgoing = re.findall(r'case "com\.ankamagames\.boufbowl\.protocol::(\w+)":\s*'
                          r'_loc2_\.type = Type\.(\w+);\s*_loc2_\.(\w+) =', union)
    for message, name, payload in outgoing:
        payloads[name] = payload
    ids = enums["BoufbowlMessage/Type"]
    envelope = {f["name"]: f for f in messages["BoufbowlMessage"]["fields"]}
    network = {}
    for name, payload in payloads.items():
        handlers = []
        for path in sorted((REFERENCE / "client").rglob("*MessageHandler.as")):
            if f"case Type.{name}:" in path.read_text():
                handlers.append(str(path.relative_to(REFERENCE)))
        network[name] = {"id": ids[name], "payload": payload,
                         "message": envelope[payload]["message"], "handlers": handlers,
                         "direction": "client_to_server" if any(n == name for _, n, _ in outgoing)
                         else "server_to_client"}
    missing = sorted({f["message"] for m in messages.values() for f in m["fields"]
                      if f["message"] and f["message"] not in messages})
    return {"format_version": 1, "framing": {"length_bytes": 4, "endian": "big",
            "max_payload_bytes": 131072}, "messages": messages, "enums": enums,
            "network": network, "external_message_types": missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--output", type=Path, default=ROOT / "protocol/client_contract.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / ".local/reverse/protocol-matrix.md")
    args = parser.parse_args()
    result = extract(args.reference)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Recovered client protocol matrix", "",
             "Generated by `python3 tools/extract_protocol.py` from the reference AS3 serializers and union mappings.",
             "Presence in this inventory does not mean the replacement service implements the message.", "",
             "| ID | Type | Direction | Payload schema | Original handler |",
             "| --- | --- | --- | --- | --- |"]
    for name, spec in sorted(result["network"].items(), key=lambda item: item[1]["id"]):
        handlers = ", ".join(Path(p).stem for p in spec["handlers"]) or "—"
        lines.append(f"| {spec['id']} | `{name}` | {spec['direction']} | `{spec['message']}` | {handlers} |")
    unmapped = sorted(set(result["enums"]["BoufbowlMessage/Type"]) - result["network"].keys())
    lines.extend(["", "Enum values without an original client union mapping: " + ", ".join(f"`{x}`" for x in unmapped) + ".", "",
                  "Full field tags, required/optional status, repeated types and source hashes are in `protocol/client_contract.json`."])
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text("\n".join(lines) + "\n")
    print(f"Recovered {len(result['messages'])} message schemas, {len(result['network'])} network types, "
          f"{len(result['enums'])} enums; external types: {result['external_message_types']}")


if __name__ == "__main__":
    main()
