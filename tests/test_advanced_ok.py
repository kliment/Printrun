"""Test suite for sending ahead of replies in `printrun/printcore.py`.

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
from printrun import gcoder
from printrun import printcore


OK = b"ok P15 B3\n"  # Firmware with room for 4 lines, BUFSIZE - 1 free when idle


class TestAdvancedOk(unittest.TestCase):
    """Checks of how many lines are outstanding, against a fake printer"""

    def setUp(self):
        patcher = mock.patch("printrun.device.Device._disable_ttyhup")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.replies = collections.deque([b"ok\n"])
        class_mock = mock.create_autospec(serial.Serial)
        self.serial = class_mock.return_value
        self.serial.is_open = True
        self.serial.readline.side_effect = self.read
        self.enterContext(mock.patch("serial.Serial", class_mock))
        self.core = printcore.printcore()
        self.addCleanup(self.core.disconnect)
        self.core.advanced_ok = True
        self.gcode = gcoder.GCode([f"G1 X{i}" for i in range(1000)])

    def read(self, *args):
        time.sleep(0.001)
        return self.replies.popleft() if self.replies else b""

    def sent_moves(self):
        return [c.args[0] for c in self.serial.write.call_args_list
                if b"G1" in c.args[0]]

    def wait_for(self, condition):
        limit = time.monotonic() + 2
        while not condition() and time.monotonic() < limit:
            time.sleep(0.002)
        self.assertTrue(condition())

    def settle(self):
        """Give the print thread time to send everything it's allowed to"""
        time.sleep(0.05)

    def start(self):
        self.core.connect("/mocked/port", 1000)
        self.wait_for(lambda: self.core.online)
        self.core.startprint(self.gcode)
        self.wait_for(lambda: self.serial.write.call_count >= 2)
        self.replies.append(OK)  # For M110, which reports the queue size
        self.wait_for(lambda: self.core.queue_lines == 4)
        self.wait_for(lambda: self.sent_moves())
        self.settle()

    def test_one_at_a_time_until_reported(self):
        """Test firmware without ADVANCED_OK gets one line per ok"""
        self.core.connect("/mocked/port", 1000)
        self.wait_for(lambda: self.core.online)
        self.core.startprint(self.gcode)
        self.wait_for(lambda: self.serial.write.call_count >= 2)
        self.replies.append(b"ok\n")
        self.wait_for(lambda: len(self.sent_moves()) == 1)
        self.settle()
        self.assertEqual(len(self.sent_moves()), 1)
        self.replies.append(b"ok\n")
        self.wait_for(lambda: len(self.sent_moves()) == 2)
        self.settle()
        self.assertEqual(len(self.sent_moves()), 2)

    def test_setting_off(self):
        """Test the option off ignores the reported queue space"""
        self.core.advanced_ok = False
        self.core.connect("/mocked/port", 1000)
        self.wait_for(lambda: self.core.online)
        self.core.startprint(self.gcode)
        self.wait_for(lambda: self.serial.write.call_count >= 2)
        self.replies.append(OK)
        self.wait_for(lambda: len(self.sent_moves()) == 1)
        self.settle()
        self.assertEqual(len(self.sent_moves()), 1)
        self.assertEqual(self.core.queue_lines, 0)

    def test_fills_queue(self):
        """Test lines are sent up to the queue size, and one more per ok"""
        self.start()
        self.assertEqual(len(self.core.unacked), 4)
        self.replies.append(OK)
        self.wait_for(lambda: len(self.core.unacked) == 4
                      and len(self.sent_moves()) == 5)
        self.settle()
        self.assertEqual(len(self.sent_moves()), 5)

    def test_serial_buffer_limit(self):
        """Test the bytes on their way stay within the firmware's buffer"""
        self.gcode = gcoder.GCode(
            [f"G1 X{i}.12345 Y{i}.12345 Z1.12345 E{i}.12345" for i in range(40)])
        self.start()
        self.assertLess(len(self.core.unacked), 4)
        self.assertLessEqual(self.core.unacked_bytes,
                             printcore.RX_BYTES_LIMIT)

    def test_serial_buffer_limit_with_lines_over_estimate(self):
        """Test lines just over the initial estimate can't pass the limit"""
        self.gcode = gcoder.GCode(
            [f"G1 X{100 + i}.123 Y{100 + i}.123 E1.123" for i in range(100)]
            + [f"G1 X1{100 + i}.1234 Y1{100 + i}.1234 E1.1234" for i in range(100)])
        self.start()
        peak = 0
        for _i in range(150):
            peak = max(peak, self.core.unacked_bytes)
            self.replies.append(OK)
            time.sleep(0.004)
        self.assertLessEqual(peak, printcore.RX_BYTES_LIMIT)

    def test_resend_after_lines_on_their_way(self):
        """Test a resend waits for the replies to the lines already sent, and
        only the first request of a burst counts"""
        self.start()
        sent = len(self.sent_moves())
        first = self.sent_moves()[0]
        self.replies.extend([b"Error:Line Number\n", b"Resend: 0\n", b"ok\n",
                             b"Error:Line Number\n", b"Resend: 0\n", b"ok\n"])
        self.wait_for(lambda: len(self.core.unacked) == 2)
        self.settle()
        self.assertEqual(len(self.sent_moves()), sent)
        self.replies.extend([b"Error:Line Number\n", b"Resend: 0\n", b"ok\n",
                             b"Error:Line Number\n", b"Resend: 0\n", b"ok\n"])
        self.wait_for(lambda: len(self.sent_moves()) > sent)
        self.assertEqual(self.sent_moves()[sent], first)
        self.settle()
        self.assertEqual(self.sent_moves()[sent + 1],
                         self.sent_moves()[1])

    def test_ok_covers_earlier_lines(self):
        """Test an ok with a line number also covers any lost before it"""
        self.start()
        self.assertEqual(self.core.unacked[0][0], 0)
        self.replies.append(b"ok N2 P15 B3\n")
        self.wait_for(lambda: self.core.last_acked == 2)
        self.settle()
        self.assertEqual(self.core.unacked[0][0], 3)
        self.assertEqual(len(self.core.unacked), 4)

    def test_no_resend_of_received_line(self):
        """Test a line isn't resent if its ok arrives after the request. The
        firmware doesn't reply to a line it already has."""
        self.start()
        self.core.send_now("M105")
        self.replies.append(b"ok N0 P15 B3\n")
        self.wait_for(lambda: b"M105\n" in [
            c.args[0] for c in self.serial.write.call_args_list])
        sent = len(self.sent_moves())
        self.replies.extend([b"Error:No Checksum\n", b"Resend: 1\n", b"ok\n"])
        self.replies.extend(b"ok N%d P15 B3\n" % n for n in range(1, sent))
        self.wait_for(lambda: len(self.sent_moves()) > sent)
        self.assertIn(b"N%d " % sent, self.sent_moves()[sent])

    def test_resend_with_discarded_lines(self):
        """Test a resend isn't held up by lines the firmware discarded, which
        it will never reply to"""
        self.start()
        sent = len(self.sent_moves())
        first = self.sent_moves()[0]
        self.replies.extend([b"Error:Line Number\n", b"Resend: 0\n", b"ok\n"])
        self.wait_for(lambda: len(self.core.unacked) == 3)
        self.settle()
        self.assertEqual(len(self.sent_moves()), sent)
        with mock.patch("printrun.printcore.RESEND_TIMEOUT", 0.05):
            self.wait_for(lambda: len(self.sent_moves()) > sent)
        self.assertEqual(self.sent_moves()[sent], first)

    def test_lost_ok(self):
        """Test sending continues after silence, if an ok never comes"""
        self.start()
        sent = len(self.sent_moves())
        self.settle()
        self.assertEqual(len(self.sent_moves()), sent)
        with mock.patch("printrun.printcore.OK_TIMEOUT", 0.05):
            self.wait_for(lambda: len(self.sent_moves()) > sent)

    def test_disconnect_stops_sending_ahead(self):
        """Test disconnecting ends the state and reports it"""
        calls = []
        self.core.callback.advancedok = calls.append
        self.start()
        self.core.disconnect()
        self.assertEqual(self.core.queue_lines, 0)
        self.assertEqual(calls, [True, False])

    def test_firmware_restart(self):
        """Test a restart goes back to one line at a time until reported"""
        self.start()
        self.replies.append(b"start\n")
        self.wait_for(lambda: self.core.queue_lines == 0)


if __name__ == '__main__':
    unittest.main()
