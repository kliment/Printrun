"""Test suite for `printrun/meatpack.py` and its use in `printrun/printcore.py`.

"""
# How to run the tests (requires Python 3.11+):
#   python3 -m unittest discover tests

# Standard libraries:
import collections
import time
import unittest
from unittest import mock

# 3rd Party/Custom libraries:
import serial
from printrun import meatpack
from printrun import printcore


class Firmware:
    """The receiving side, following Marlin's feature/meatpack.cpp"""

    def __init__(self):
        self.active = False
        self.no_spaces = False
        self.text = bytearray()
        self.cmd_count = 0
        self.cmd_is_next = False
        self.full_char_count = 0
        self.second_char = None

    def table(self):
        space = b"E" if self.no_spaces else b" "
        return b"0123456789." + space + b"\nGX"

    def feed(self, data):
        for byte in data:
            if byte == 0xFF:
                if self.cmd_count:
                    self.cmd_is_next = True
                    self.cmd_count = 0
                else:
                    self.cmd_count = 1
                continue
            if self.cmd_is_next:
                self.command(byte)
                self.cmd_is_next = False
                continue
            if self.cmd_count:
                self.inner(0xFF)
                self.cmd_count = 0
            self.inner(byte)

    def command(self, byte):
        if byte == 0xFB:
            self.active = True
        elif byte == 0xFA:
            self.active = False
        elif byte == 0xF9:
            self.active = self.no_spaces = False
            self.full_char_count = 0
            self.second_char = None
        elif byte == 0xF7:
            self.no_spaces = True
        elif byte == 0xF6:
            self.no_spaces = False

    def inner(self, byte):
        if not self.active:
            self.text.append(byte)
            return
        if self.full_char_count:
            self.text.append(byte)
            if self.second_char is not None:
                self.text.append(self.second_char)
                self.second_char = None
            self.full_char_count -= 1
            return
        low, high = byte & 0xF, byte >> 4
        table = self.table()
        if low == 0xF:
            self.full_char_count = 1
            if high == 0xF:
                self.full_char_count = 2
            else:
                self.second_char = table[high]
            return
        self.text.append(table[low])
        if table[low] != ord("\n"):
            if high == 0xF:
                self.full_char_count = 1
            else:
                self.text.append(table[high])


def unpack(*lines):
    """Pack lines and return the text the firmware reads from them"""
    firmware = Firmware()
    firmware.feed(meatpack.ENABLE_NO_SPACES + meatpack.ENABLE_PACKING)
    for line in lines:
        firmware.feed(meatpack.pack(line))
    return bytes(firmware.text)


class TestPack(unittest.TestCase):
    """Checks that packed lines come back unchanged"""

    def test_round_trip(self):
        """Test even and odd lengths, and characters in and out of the table"""
        for line in (b"\n",
                     b"G\n",
                     b"M\n",
                     b"G1\n",
                     b"M1\n",
                     b"MS\n",
                     b"G1X1.5Y2.25E0.012\n",
                     b"G1X1.5Y2.25E0.01F\n",
                     b"N12G1X-1.5*33\n",
                     b"M117 Hello, world!\n",
                     b"M23 FILE.GCO\n",
                     b"ab\n",
                     b"abc\n"):
            with self.subTest(line=line):
                self.assertEqual(unpack(line), line)

    def test_every_ascii_character(self):
        """Test all characters a line can hold, in both positions of a byte"""
        chars = bytes(c for c in range(1, 128) if c != ord("\n"))
        for line in (chars, b"0" + chars):
            self.assertEqual(unpack(line + b"\n"), line + b"\n")

    def test_lines_in_sequence(self):
        """Test that lines stay in step with the ones before them"""
        lines = (b"G1X1\n", b"M105\n", b"G1X1.5\n", b"M\n", b"G\n", b"T0\n")
        self.assertEqual(unpack(*lines), b"".join(lines))

    def test_no_double_command_byte(self):
        """Test that a packed line never looks like the start of a command"""
        chars = bytes(c for c in range(1, 128) if c != ord("\n"))
        self.assertNotIn(b"\xff\xff", meatpack.pack(chars * 2 + b"\n"))

    def test_size(self):
        """Test that a move takes close to half the bytes"""
        line = meatpack.strip_spaces("G1 X120.125 Y100.5 E1.25") + "\n"
        original = len("G1 X120.125 Y100.5 E1.25\n")
        self.assertLessEqual(len(meatpack.pack(line.encode())), original * 0.6)

    def test_strip_spaces(self):
        """Test that only moves lose their spaces"""
        for command, expected in (("G0 X1", "G0X1"),
                                  ("G1 X1 Y2 E3", "G1X1Y2E3"),
                                  ("G2 X1 I2", "G2X1I2"),
                                  ("G3 X1 J2", "G3X1J2"),
                                  ("G28 X", "G28 X"),
                                  ("M117 G1 X1", "M117 G1 X1"),
                                  ("M23 A B.GCO", "M23 A B.GCO")):
            with self.subTest(command=command):
                self.assertEqual(meatpack.strip_spaces(command), expected)

    def test_is_emergency(self):
        """Test which commands bypass packing"""
        for command in ("M108", "M112", "M410", "M876 S1", "N5 M112*33"):
            with self.subTest(command=command):
                self.assertTrue(meatpack.is_emergency(command))
        for command in ("M1080", "M105", "G1 X1", "M117 M112"):
            with self.subTest(command=command):
                self.assertFalse(meatpack.is_emergency(command))


class TestPrintcore(unittest.TestCase):
    """Checks of the negotiation in printcore against a fake printer"""

    CAPABLE = b"Cap:MEATPACK:1\n"

    def setUp(self):
        patcher = mock.patch("printrun.device.Device._disable_ttyhup")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.replies = collections.deque([b"ok\n"])
        self.serial = self.mock_serial()
        self.core = printcore.printcore()
        self.addCleanup(self.core.disconnect)
        self.core.meatpack = True

    def mock_serial(self):
        class_mock = mock.create_autospec(serial.Serial)
        instance = class_mock.return_value
        instance.is_open = True
        instance.readline.side_effect = self.read
        self.enterContext(mock.patch("serial.Serial", class_mock))
        return instance

    def read(self, *args):
        time.sleep(0.002)
        return self.replies.popleft() if self.replies else b""

    def written(self):
        return b"".join(c.args[0] for c in self.serial.write.call_args_list)

    def firmware_text(self):
        firmware = Firmware()
        firmware.feed(self.written())
        return bytes(firmware.text), firmware

    def wait_for(self, condition):
        limit = time.monotonic() + 2
        while not condition() and time.monotonic() < limit:
            time.sleep(0.002)
        self.assertTrue(condition())

    def connect(self, capable=True):
        self.core.connect("/mocked/port", 1000)
        self.wait_for(lambda: self.core.online)
        self.wait_for(lambda: b"M115\n" in self.written())
        if capable:
            self.replies.append(self.CAPABLE)
            self.wait_for(lambda: self.core.meatpack_active)

    def test_disabled_sends_plain(self):
        """Test that nothing changes on the wire with the setting off"""
        self.core.meatpack = False
        self.core.connect("/mocked/port", 1000)
        self.wait_for(lambda: self.core.online)
        self.replies.append(self.CAPABLE)
        self.core.send_now("G1 X1")
        self.wait_for(lambda: b"G1 X1\n" in self.written())
        self.assertFalse(self.core.meatpack_active)
        self.assertNotIn(b"\xff", self.written())

    def test_firmware_without_meatpack(self):
        """Test that lines stay plain if the firmware doesn't report it"""
        self.connect(capable=False)
        self.replies.append(b"Cap:MEATPACK:0\n")
        self.core.send_now("G1 X1")
        self.wait_for(lambda: b"G1 X1\n" in self.written())
        self.assertFalse(self.core.meatpack_active)

    def test_packs_after_negotiation(self):
        """Test the firmware reads packed commands, moves without spaces"""
        self.connect()
        self.core.send_now("G1 X1.5 Y2")
        self.core.send_now("M117 Two words")
        self.wait_for(lambda: self.core.priqueue.empty())
        self.wait_for(lambda: self.firmware_text()[0].endswith(b"words\n"))
        self.assertTrue(self.firmware_text()[0].endswith(
            b"M115\nG1X1.5Y2\nM117 Two words\n"))
        self.assertTrue(self.firmware_text()[1].active)

    def test_checksum_matches_sent_line(self):
        """Test the checksum covers the line as the firmware receives it"""
        self.connect()
        # pylint: disable-next=protected-access
        self.core._send("G1 X1 Y2", 7, True)
        line = "N7 G1X1Y2"
        # pylint: disable-next=protected-access
        expected = f"{line}*{self.core._checksum(line)}\n".encode()
        self.assertTrue(self.firmware_text()[0].endswith(expected))

    def test_emergency_is_unpacked(self):
        """Test the raw stream holds the emergency command on its own line"""
        self.connect()
        self.core.send_now("M112")
        self.wait_for(lambda: b"\nM112\n" in self.written())
        text, firmware = self.firmware_text()
        self.assertTrue(text.endswith(b"\nM112\n"))
        self.assertTrue(firmware.active)

    def test_state_callback(self):
        """Test the callback follows packing on, restart and disconnect"""
        calls = []
        self.core.callback.meatpack = calls.append
        self.connect()
        self.assertEqual(calls, [True])
        self.replies.append(b"start\n")
        self.wait_for(lambda: calls == [True, False])
        self.wait_for(lambda: self.written().endswith(b"M115\n"))
        self.replies.append(self.CAPABLE)
        self.wait_for(lambda: calls == [True, False, True])
        self.core.disconnect()
        self.assertEqual(calls, [True, False, True, False])

    def test_query_while_plain(self):
        """Test a query is sent with a newline to end the line for firmware
        without MeatPack"""
        self.connect(capable=False)
        self.core.meatpack_query()
        self.assertTrue(self.written().endswith(meatpack.QUERY_CONFIG + b"\n"))

    def test_query_while_packing(self):
        """Test a query leaves later packed lines readable"""
        self.connect()
        self.core.meatpack_query()
        self.assertTrue(self.written().endswith(meatpack.QUERY_CONFIG))
        self.core.send_now("M105")
        self.wait_for(lambda: self.firmware_text()[0].endswith(b"\nM105\n"))

    def test_resend_resets_unpacking(self):
        """Test a resent line is read correctly after the firmware discarded
        part of an earlier line, leaving it waiting for a byte"""
        self.connect()
        firmware = Firmware()
        firmware.feed(meatpack.ENABLE_NO_SPACES + meatpack.ENABLE_PACKING)
        firmware.feed(meatpack.pack(b"N5 G1X1*7\n")[:1])  # Its literal N is lost
        self.assertEqual(firmware.full_char_count, 1)
        self.serial.write.reset_mock()
        self.replies.append(b"Resend: 5\n")
        self.wait_for(lambda: self.core.meatpack_resync)
        self.core.send_now("M105")
        self.wait_for(lambda: self.serial.write.called)
        firmware.text.clear()
        firmware.feed(self.written())
        self.assertEqual(bytes(firmware.text), b"M105\n")
        self.assertTrue(firmware.active)
        self.assertTrue(firmware.no_spaces)

    def test_firmware_restart(self):
        """Test a restart goes back to plain lines and negotiates again"""
        self.connect()
        self.replies.append(b"start\n")
        self.wait_for(lambda: not self.core.meatpack_active)
        self.wait_for(lambda: self.written().endswith(b"M115\n"))
        self.replies.append(self.CAPABLE)
        self.wait_for(lambda: self.core.meatpack_active)

    def test_disconnect_returns_to_plain(self):
        """Test the firmware is left reading plain text"""
        self.connect()
        self.core.disconnect()
        firmware = self.firmware_text()[1]
        self.assertFalse(firmware.active)
        self.assertFalse(firmware.no_spaces)

    def test_connect_clears_earlier_state(self):
        """Test a connection recovers firmware left in packed mode"""
        firmware = Firmware()
        firmware.feed(meatpack.ENABLE_NO_SPACES + meatpack.ENABLE_PACKING)
        self.core.connect("/mocked/port", 1000)
        self.wait_for(lambda: self.serial.write.called)
        firmware.feed(self.serial.write.call_args_list[0].args[0])
        self.assertFalse(firmware.active)
        self.assertFalse(firmware.no_spaces)


if __name__ == '__main__':
    unittest.main()
