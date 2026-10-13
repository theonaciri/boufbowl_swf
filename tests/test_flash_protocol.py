import struct
import unittest

from tools.build_mock_fixture import build_fixture
from tools.flash_protocol import Codec, FrameDecoder, ProtocolError, frame, varint


class FlashProtocolTests(unittest.TestCase):
    def setUp(self):
        self.codec = Codec()

    def test_original_grid_tags_and_zigzag_known_vector(self):
        self.assertEqual(self.codec.encode("GridCoordinates", {"x": -5, "y": 2}), bytes.fromhex("08091004"))
        self.assertEqual(self.codec.decode("GridCoordinates", bytes.fromhex("08091004")), {"x": -5, "y": 2})

    def test_identity_above_javascript_precision_remains_exact(self):
        payload = {"boufbowlerId": "9007199254740993"}
        encoded = self.codec.encode("Order", payload)
        self.assertEqual(encoded.hex(), "088180808080808010")
        self.assertEqual(self.codec.decode("Order", encoded), payload)

    def test_packed_enum_array_is_accepted_by_original_contract(self):
        self.assertEqual(self.codec.decode("RegularOrderData", bytes.fromhex("1203010204")), {"elements": [1, 2, 4]})

    def test_fragmented_and_coalesced_big_endian_frames(self):
        encoded = self.codec.envelope("RESOLUTION_DONE", {"turn": 1})
        framed = frame(encoded)
        self.assertEqual(framed[:4], struct.pack(">I", len(encoded)))
        decoder = FrameDecoder()
        self.assertEqual(decoder.feed(framed[:3]), [])
        self.assertEqual(decoder.feed(framed[3:] + framed), [encoded, encoded])

    def test_invalid_lengths_and_truncated_payloads_are_rejected(self):
        for length in (0, 131073, 0xffffffff):
            with self.assertRaises(ProtocolError):
                FrameDecoder().feed(struct.pack(">I", length))
        with self.assertRaises(ProtocolError):
            self.codec.decode("GridCoordinates", bytes.fromhex("0880"))

    def test_envelope_discriminator_must_match_exactly_one_payload(self):
        encoded = self.codec.encode("BoufbowlMessage", {"type": 2701, "introductionDone": {}})
        with self.assertRaises(ProtocolError):
            self.codec.open_envelope(encoded)

    def test_duplicate_fields_and_incorrect_wire_types_are_rejected(self):
        for encoded in (bytes.fromhex("080108021002"), bytes.fromhex("0a01001002")):
            with self.assertRaises(ProtocolError):
                self.codec.decode("GridCoordinates", encoded)

    def test_unknown_fields_are_skipped_like_original_reader(self):
        encoded = bytes.fromhex("08091004") + varint(99 << 3) + varint(123)
        self.assertEqual(self.codec.decode("GridCoordinates", encoded), {"x": -5, "y": 2})

    def test_required_fields_invalid_numbers_and_typos_fail(self):
        for payload in ({"x": 1}, {"x": True, "y": 0}, {"x": 1 << 31, "y": 0}, {"x": 0, "y": 0, "z": 0}):
            with self.assertRaises(ProtocolError):
                self.codec.encode("GridCoordinates", payload)

    def test_fixture_enters_match_and_waits_for_resolution_ack(self):
        fixture = build_fixture()
        messages = [self.codec.open_envelope(bytes.fromhex(s["hex"])) for s in fixture["steps"]]
        self.assertEqual([m["type"] for m in messages], ["MATCH_INFORMATION", "FIELD_STATE", "RESOLUTION_SCENARIO", "FIELD_STATE", "MATCH_END"])
        self.assertTrue(messages[0]["payload"]["skipIntro"])
        self.assertEqual(messages[0]["payload"]["id"], "9007199254740993")
        self.assertEqual(len(messages[2]["payload"]["boufbowlerTracks"]), 10)
        self.assertEqual(fixture["steps"][3]["wait_for"], "ResolutionDoneMessage")


if __name__ == "__main__":
    unittest.main()
