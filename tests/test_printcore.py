"""Test suite for `printrun/printcore.py`.

It also serves as a test for printrun.eventhandler.PrinterEventHandler.

"""
# How to run the tests (requires Python 3.11+):
#   python3 -m unittest discover tests

# Standard libraries:
import random
import socket
import time
import unittest
from unittest import mock

# 3rd Party/Custom libraries:
import serial
from printrun import eventhandler
from printrun import gcoder
from printrun import printcore


DEFAULT_ANSWER = 'ok:\n'
CNC_PROCESS_TIME = 0.02  # in s


def slow_printer(*args):
    """Simulate a slow processing printer"""
    time.sleep(CNC_PROCESS_TIME*random.randint(0, 90)/100)
    return DEFAULT_ANSWER.encode()


def wait_printer_cycles(cycles):
    """Wait for a slow printer to process"""
    time.sleep(CNC_PROCESS_TIME*cycles)


def mock_sttyhup(cls):
    """Fake stty control"""
    # Needed to avoid error:
    # "stty: /mocked/port: No such file or directory"
    cls.enterClassContext(
        mock.patch("printrun.printcore.control_ttyhup"))


def mock_serial(test, read_function=slow_printer):
    """Fake Serial device with slow response and always open"""
    class_mock = mock.create_autospec(serial.Serial)
    instance_mock = class_mock.return_value
    instance_mock.readline.side_effect = read_function
    instance_mock.is_open = True
    return test.enterContext(mock.patch("serial.Serial", class_mock))


def mock_socket(test, read_function=slow_printer):
    """Fake socket with slow response"""
    class_mock = mock.create_autospec(socket.socket)
    instance_mock = class_mock.return_value
    socket_file = instance_mock.makefile.return_value
    socket_file.read.side_effect = read_function
    return test.enterContext(mock.patch("socket.socket", class_mock))


def add_mocked_handler(core):
    """Add a fake PrinterEventHandler to a printcore instance"""
    mocked_handler = mock.create_autospec(
        spec=eventhandler.PrinterEventHandler)
    core.addEventHandler(mocked_handler)
    return mocked_handler


def mock_callback(test, core, callback, **kwargs):
    """Fake a callback function of a printcore instance"""
    # Parameters
    #   test: unittest.TestCase instance
    #   core: printcore.printcore instance
    #   callback: string with callback name, e.g. "onlinecb"
    return test.enterContext(mock.patch.object(core, callback, **kwargs))


def fake_preprintsend(gline, *args):
    """Dummy function that returns its first argument"""
    return gline


def assert_equal_glines(test, gline_a, gline_b):
    """Check if two gcoder.Lines are equal"""
    # Had to work around the two gline objects being "different". gcoder.Line
    # objects don't have comparison built in and are seen as different even
    # though they contain the same information
    test.assertTrue(gline_a.raw == gline_b.raw)


def subtest_mock(test, msg, mocks, check, *args):
    """Perform same test on a list of mocked objects"""
    for item in mocks:
        with test.subTest(msg, mock=item):
            getattr(item, check)(*args)


def setup_serial_core(test):
    """Set up printcore and connect it to a with a fake Serial"""
    core = printcore.printcore()
    test.addCleanup(core.disconnect)
    mocked_serial = mock_serial(test)
    core.connect("/mocked/port", 1000)
    wait_printer_cycles(2)
    return core, mocked_serial


def setup_socket_core(test):
    """Set up printcore and connect it to a with a fake socket"""
    core = printcore.printcore()
    test.addCleanup(core.disconnect)
    mocked_socket = mock_socket(test)
    core.connect("1.2.3.4:56", 1000)
    wait_printer_cycles(2)
    return core, mocked_socket


def setup_test_command():
    """Set up a command to test"""
    command = "Random Command"
    parsed_command = f"{command}\n".encode('ascii')
    parsed_gline = gcoder.GCode().append(command, store=False)
    return {'raw': command,
            'parsed': parsed_command,
            'gline': parsed_gline}


def checksum_command(command, lineno=0):
    """Add line number and checksum to a command"""
    core = printcore.printcore()
    prefixed_command = f"N{lineno} {command}"
    # pylint: disable-next=protected-access
    checksum = str(core._checksum(prefixed_command))
    checksummed_command = f"{prefixed_command}*{checksum}\n"
    return checksummed_command.encode('ascii')


class TestInit(unittest.TestCase):
    """Functional checks for printcore's constructor"""

    def test_handler_on_init(self):
        """Test that the `on_init` event is triggered"""
        mocked_handler = mock.Mock(spec=eventhandler.PrinterEventHandler)
        with mock.patch('printrun.printcore.PRINTCORE_HANDLER',
                        [mocked_handler]):
            printcore.printcore()
        mocked_handler.on_init.assert_called_once()


class TestConnect(unittest.TestCase):
    """Functional checks for the connect method"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.core = printcore.printcore()

    def test_connection_events(self):
        """Test events on a successful connection"""
        mock_serial(self)
        mocked_handler = add_mocked_handler(self.core)
        online_cb = mock_callback(self, self.core, "onlinecb")
        self.core.connect("/mocked/port", 1000)
        wait_printer_cycles(2)

        with self.subTest("Check `online` is set"):
            self.assertTrue(self.core.online)

        with self.subTest("Check read and send threads started"):
            self.assertIsNotNone(self.core.read_thread)
            self.assertTrue(self.core.read_thread.is_alive)
            self.assertIsNotNone(self.core.send_thread)
            self.assertTrue(self.core.send_thread.is_alive)

        with self.subTest("Check the `on_connect` event is triggered"):
            mocked_handler.on_connect.assert_called_once()

        subtest_mock(self, "Check triggering the `online` event/callback",
                     (mocked_handler.on_online, online_cb),
                     "assert_called_once")

    def test_calls_socket_connect(self):
        """Test that socket.socket.connect() is called"""
        mocked_socket = mock_socket(self)
        url = ("192.168.1.200", 1234)
        self.core.connect(f"{url[0]}:{url[1]}", 1000)
        wait_printer_cycles(2)

        with self.subTest("Check the socket is opened"):
            mocked_socket.return_value.connect.assert_called_once_with(url)

        with self.subTest("Check underlying file-like resource is opened"):
            mocked_socket.return_value.makefile.assert_called_once()

    def test_calls_serial_open(self):
        """Test that serial.Serial.open() is called"""
        mocked_serial = mock_serial(self)
        self.core.connect("/mocked/port", 1000, 1)
        wait_printer_cycles(2)
        mocked_serial.return_value.open.assert_called_once()

    def test_bad_ports(self):
        """Test that an error is logged if connection fails"""
        for port in ("/mocked/port", "1.2.3.4:56"):
            with self.subTest(port=port):
                with self.assertLogs(level="ERROR"):
                    self.core.connect(port, 1000)

    def test_ioerror(self):
        """Test that an error is logged if connection fails with IOError"""
        mocked_serial = mock_serial(self)
        mocked_serial.return_value.open.side_effect = IOError
        with self.assertLogs(level="ERROR"):
            self.core.connect("/mocked/port", 1000)

    def test_no_port(self):
        """Silent on attempting to connect to nothing"""
        self.core.connect()

    def test_already_connected(self):
        """Test that a previous connection is disconnected"""
        mock_serial(self)
        first_port = "/first/port"
        second_port = "/second/port"
        self.core.connect(first_port, 1000)
        wait_printer_cycles(2)
        self.assertEqual(self.core.printer.port, first_port)
        self.core.connect(second_port, 1000)
        wait_printer_cycles(4)
        self.assertEqual(self.core.printer.port, second_port)

    def test_handler_on_error(self):
        """Test that the `error` event and callback are triggered"""
        err_msg = "Not connected to printer."
        mocked_cb = mock_callback(self, self.core, "errorcb")
        mocked_handler = add_mocked_handler(self.core)
        self.core.send_now("Random Command")
        subtest_mock(self, "", (mocked_handler.on_error, mocked_cb),
                     "assert_called_once_with", err_msg)

    def tearDown(self):
        self.core.disconnect()
        self.core.eventhandler = []  # empty eventhandler


class TestDisconnect(unittest.TestCase):
    """Functional checks for the disconnect method"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.core, self.mocked_serial = setup_serial_core(self)

    def test_calls_serial_close(self):
        """Test that serial.Serial.close() is called"""
        self.core.disconnect()
        self.mocked_serial.return_value.close.assert_called_once()

    def test_calls_socket_close(self):
        """Test that socket.socket.close() is called"""
        core, mocked_socket = setup_socket_core(self)
        core.disconnect()
        wait_printer_cycles(2)

        with self.subTest("Check the socket is closed"):
            mocked_socket.return_value.close.assert_called_once()

        with self.subTest("Check underlying file-like resource is closed"):
            socket_file = mocked_socket.return_value.makefile.return_value
            socket_file.close.assert_called_once()

    def test_disconnection_events(self):
        """Test events on a successful disconnection"""
        mocked_handler = add_mocked_handler(self.core)
        with self.subTest("Check `online` was set before test"):
            self.assertTrue(self.core.online)

        self.core.disconnect()

        with self.subTest("Check `online` is unset"):
            self.assertFalse(self.core.online)

        with self.subTest("Check the `on_disconnect` event is triggered"):
            mocked_handler.on_disconnect.assert_called_once()

        with self.subTest("Check read and send threads were removed"):
            self.assertIsNone(self.core.read_thread)
            self.assertIsNone(self.core.send_thread)

    def test_disconnect_error(self):
        """Test that an error is logged if disconnection fails"""
        with (
            mock.patch.object(self.mocked_serial.return_value, "close",
                              side_effect=serial.SerialException),
            self.assertLogs(level="ERROR")
        ):
            self.core.disconnect()
        # Check that `online` is unset even after an error
        self.assertFalse(self.core.online)


class TestSends(unittest.TestCase):
    """Functional checks for send and send_now methods"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)
        cls.command = setup_test_command()['raw']

    def setUp(self):
        self.core, self.mocked_serial = setup_serial_core(self)

    def test_send_now_priqueue(self):
        """Test that a command is put into `priqueue`"""
        with mock.patch.object(self.core, "priqueue") as mocked_queue:
            self.core.send_now(self.command)
        mocked_queue.put_nowait.assert_called_once_with(self.command)

    def test_send_priqueue(self):
        """Test that a command is put into `priqueue` when not printing"""
        with mock.patch.object(self.core, "priqueue") as mocked_queue:
            self.assertFalse(self.core.printing)
            self.core.send(self.command)
        mocked_queue.put_nowait.assert_called_once_with(self.command)

    def test_send_mainqueue(self):
        """Test that a command is put into `mainqueue` when printing"""
        with (
            mock.patch.object(self.core, "printing", True),
            mock.patch.object(self.core, "mainqueue") as mocked_queue
        ):
            self.assertTrue(self.core.printing)
            self.core.send(self.command)
            mocked_queue.append.assert_called_once_with(self.command)

    def test_send_now_not_connected(self):
        """Test that an error is logged when attempting to send a
        command but printer is not online"""
        core = printcore.printcore()
        with self.assertLogs(level="ERROR"):
            core.send_now("Random Command")

    def test_send_not_connected(self):
        """Test that an error is logged when attempting to send a
        command but printer is not online"""
        core = printcore.printcore()
        with self.assertLogs(level="ERROR"):
            core.send("Random Command")


class TestPrint(unittest.TestCase):
    """Functional checks for startprint, cancelprint, pause and resume
    methods"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

        # print_code     parsed_print_code
        # ----------     -----------------
        # "G0 X0"        b'N0 G0 X0*97\n'
        # "G0 X1"        b'N1 G0 X1*97\n'
        # "G0 X2"        b'N2 G0 X2*97\n'
        # "G0 X3"        b'N3 G0 X3*97\n'
        #   ...                 ...

        cls.print_layer_count = 10
        tmp = []
        for i in range(cls.print_layer_count):
            tmp = tmp + [
                f"G1 Z{i}",  # move to layer (i)
                "G0 X1",
                f"G1 X100 E{i+1}",
            ]
        cls.print_line_count = len(tmp)
        cls.print_code = gcoder.GCode(tmp)

        cls.parsed_print_code = []
        for i in range(cls.print_line_count):
            command = cls.print_code.lines[i].raw
            cls.parsed_print_code.append(checksum_command(command, i))

    def setUp(self):
        self.core, self.mocked_serial = setup_serial_core(self)
        self.mocked_handler = add_mocked_handler(self.core)
        self.start_cb = mock_callback(self, self.core, "startcb")
        self.end_cb = mock_callback(self, self.core, "endcb")

    def check_unfinished_print(self):
        """Check the first command was sent but the last wasn't"""
        first_call = mock.call(self.parsed_print_code[0])
        last_call = mock.call(
            self.parsed_print_code[self.print_line_count-1])
        write_calls = self.mocked_serial.return_value.write.mock_calls
        self.assertIn(first_call, write_calls)
        self.assertNotIn(last_call, write_calls)

    def check_finished_print(self):
        """Check that all commands were sent to the printer"""
        for line in self.parsed_print_code:
            self.mocked_serial.return_value.write.assert_any_call(line)

    def test_start_finish(self):
        """Test events from print start to finish"""
        layerchange_cb = mock_callback(self, self.core, "layerchangecb")
        preprintsend_cb = mock_callback(self, self.core, "preprintsendcb",
                                        side_effect=fake_preprintsend)
        printsend_cb = mock_callback(self, self.core, "printsendcb")

        with self.subTest("Check `printing` was unset before test"):
            self.assertFalse(self.core.printing)

        with self.subTest("Check startprint returns True on success"):
            self.assertTrue(self.core.startprint(self.print_code))

        # Wait for the print to commence
        wait_printer_cycles(4)

        with self.subTest("Check `printing` is set"):
            self.assertTrue(self.core.printing)

        subtest_mock(self, "Check triggering `start` event/callback",
                     (self.start_cb, self.mocked_handler.on_start),
                     "assert_called_once_with", False)

        # Let the print finish
        wait_printer_cycles(self.print_line_count*1.5)

        with self.subTest("Check that serial.Serial.write() was called"):
            self.check_finished_print()

        subtest_mock(self, "Check triggering `end` event/callback",
                     (self.end_cb, self.mocked_handler.on_end),
                     "assert_called_once")

        for item in (self.mocked_handler.on_layerchange, layerchange_cb):
            with self.subTest("Check triggering `layerchange` event/callback",
                              mock=item):
                for i in range(1, self.print_layer_count):
                    item.assert_any_call(i)

        with self.subTest("Check triggering `preprintsend` event"):
            event = self.mocked_handler.on_preprintsend
            # Had to use this workaround. See test_handler_on_send
            for i in range(self.print_line_count):
                # Get the arguments from the ith call to event
                call_args = event.call_args_list[i].args
                # Check the arguments of the call are as expected
                assert_equal_glines(self, call_args[0],
                                    self.core.mainqueue.lines[i])
                self.assertEqual(call_args[1], i)
                self.assertEqual(call_args[2], self.core.mainqueue)

        with self.subTest("Check triggering `preprintsend` callback"):
            # Had to use this workaround. See test_handler_on_send
            for i in range(self.print_line_count-1):
                # Get the arguments from the ith call to callback
                call_args = preprintsend_cb.call_args_list[i].args
                # Check the arguments of the call are as expected
                assert_equal_glines(self, call_args[0],
                                    self.core.mainqueue.lines[i])
                assert_equal_glines(self, call_args[1],
                                    self.core.mainqueue.lines[i+1])
            i = self.print_line_count - 1
            last_call_args = preprintsend_cb.call_args_list[i].args
            assert_equal_glines(self, last_call_args[0],
                                self.core.mainqueue.lines[i])
            self.assertEqual(last_call_args[1], None)

        for item in (self.mocked_handler.on_printsend, printsend_cb):
            with self.subTest("Check triggering `printsend` event/callback",
                              mock=item):
                # Had to use this workaround. See test_handler_on_send
                for i in range(self.print_line_count):
                    # Get the arguments from the ith call to event
                    call_args = item.call_args_list[i].args
                    assert_equal_glines(self, call_args[0],
                                        self.core.mainqueue.lines[i])

    def test_start_startindex(self):
        """Test that only commands after resume point are sent to the
        printer"""

        # print_code     parsed_print_code
        # ----------     -----------------
        # "G0 X0"            not sent
        # "G0 X1"            not sent
        # "G0 X2"        b'N0 G0 X2*99\n'
        # "G0 X3"        b'N1 G0 X3*99\n'
        #   ...                 ...

        resume_index = 2  # resume_index < self.print_line_count
        parsed_print_code = []
        lineno = 0
        for i in range(resume_index, self.print_line_count):
            command = self.print_code.lines[i].raw
            parsed_print_code.append(checksum_command(command, lineno))
            lineno += 1

        self.core.startprint(self.print_code, startindex=resume_index)
        wait_printer_cycles(self.print_line_count*1.5)
        for line in parsed_print_code:
            self.mocked_serial.return_value.write.assert_any_call(line)

    def test_start_already_printing(self):
        """Test startprint returns False if already printing"""
        self.core.startprint(self.print_code)
        self.assertFalse(self.core.startprint(self.print_code))

    def test_start_offline(self):
        """Test startprint returns False if not connected"""
        core = printcore.printcore()
        self.assertFalse(core.startprint(self.print_code))

    def test_pause_resume(self):
        """Test events during pausing and resuming a print"""
        self.core.startprint(self.print_code)
        wait_printer_cycles(6)

        with self.subTest("Check `paused` is unset before pausing"):
            self.assertFalse(self.core.paused)

        with self.subTest("Check `printing` is set before pausing"):
            self.assertTrue(self.core.printing)

        # Pause mid print
        self.core.pause()
        wait_printer_cycles(6)

        with self.subTest("Check `paused` is set after pausing"):
            self.assertTrue(self.core.paused)

        with self.subTest("Check `printing` is unset after pausing"):
            self.assertFalse(self.core.printing)

        with self.subTest("Check print didn't finish yet"):
            self.check_unfinished_print()

        subtest_mock(self, "Check triggering `end` event/callback on pause",
                     (self.mocked_handler.on_end, self.end_cb),
                     "assert_called_once")

        # Resume print
        self.core.resume()
        wait_printer_cycles(6)

        with self.subTest("Check `paused` is unset after resuming"):
            self.assertFalse(self.core.paused)

        with self.subTest("Check `printing` is set after resuming"):
            self.assertTrue(self.core.printing)

        subtest_mock(self, "Check `start` event/callback when resuming",
                     (self.start_cb, self.mocked_handler.on_start),
                     "assert_called_with", True)

        # Let the print finish
        wait_printer_cycles(self.print_line_count*1.5)

        with self.subTest("Check that `resume` finishes the print"):
            self.check_finished_print()

    def test_resume_offline(self):
        """Test resume returns False if not connected"""
        core = printcore.printcore()
        self.assertFalse(core.resume())

    def test_pause_offline(self):
        """Test pause returns False if not connected"""
        core = printcore.printcore()
        self.assertFalse(core.pause())

    def test_cancel(self):
        """Test events after canceling a print"""
        # Start a print and cancel it mid-print
        self.core.startprint(self.print_code)
        wait_printer_cycles(self.print_line_count/3)
        self.core.cancelprint()
        wait_printer_cycles(6)

        with self.subTest("Check `printing` is unset"):
            self.assertFalse(self.core.printing)

        with self.subTest("Check `paused` is unset"):
            self.assertFalse(self.core.paused)

        with self.subTest("Check `mainqueue` is deleted"):
            self.assertIsNone(self.core.mainqueue)

        with self.subTest("Check the print is unfinished"):
            self.check_unfinished_print()

        subtest_mock(self, "Test triggering `end` event/callback",
                     (self.mocked_handler.on_end, self.end_cb),
                     "assert_called_once")

    def test_host_command(self):
        """Test calling host-commands"""
        print_lines = []
        for i in range(2):
            print_lines.append(f"G1 X{i}")
        print_lines.append(';@pause')
        print_code = gcoder.GCode(print_lines)
        self.core.startprint(print_code)
        wait_printer_cycles(len(print_lines)*2)
        self.assertTrue(self.core.paused)


class TestReset(unittest.TestCase):
    """Functional checks for the reset method"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.core, self.mocked_serial = setup_serial_core(self)

    def test_calls_serial_dtr(self):
        """Check that reset sets DTR attribute to zero"""
        self.core.reset()
        # check the DTR attribute was disabled
        mocked_dtr = self.mocked_serial.return_value.dtr
        self.assertEqual(mocked_dtr, 0)


class TestSendThread(unittest.TestCase):
    """Functional checks for the sending thread"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)
        test_command = setup_test_command()
        cls.command = test_command['raw']
        cls.parsed_command = test_command['parsed']
        cls.parsed_gline = test_command['gline']

    def setUp(self):
        self.core, self.mocked_serial = setup_serial_core(self)

    def test_priority_command(self):
        """Test that commands are sent to the printer from priqueue"""
        self.core.send_now(self.command)
        wait_printer_cycles(2)
        self.mocked_serial.return_value.write.assert_called_with(
            self.parsed_command)
        self.assertTrue(self.core.writefailures == 0)

    def test_calls_socket_write(self):
        """Test that socket file resource is written to"""
        core, mocked_socket = setup_socket_core(self)
        socket_file = mocked_socket.return_value.makefile.return_value
        core.send_now(self.command)
        wait_printer_cycles(2)
        socket_file.write.assert_called_with(self.parsed_command)
        self.assertTrue(self.core.writefailures == 0)

    def test_handler_on_send(self):
        """Test that the `on_send` event is triggered"""
        mocked_handler = add_mocked_handler(self.core)
        mocked_cb = mock_callback(self, self.core, "sendcb")
        self.core.send_now(self.command)
        wait_printer_cycles(2)

        # Ideal code:
        #     func = mocked_handler.on_send
        #     func.assert_called_once_with(self.command, self.parsed_gline)
        #
        # Had to use a workaround. See `compare_glines`
        for item in (mocked_handler.on_send, mocked_cb):
            with self.subTest("Check triggering `send` event/callback",
                              mock=item):
                self.assertEqual(self.command, item.call_args.args[0])
                assert_equal_glines(self, self.parsed_gline,
                                    item.call_args.args[1])

    def test_write_serial_error(self):
        """Test an error is logged when serial error during writing"""
        with (
              mock.patch.object(self.mocked_serial.return_value, "write",
                                side_effect=serial.SerialException),
              self.assertLogs(level="ERROR")
        ):
            self.core.send(self.command)
            wait_printer_cycles(2)
        self.assertEqual(self.core.writefailures, 1)

    def test_write_socket_error(self):
        """Test an error is logged when socket error during writing"""
        core, mocked_socket = setup_socket_core(self)
        socket_file = mocked_socket.return_value.makefile.return_value
        with (
              mock.patch.object(socket_file, "write",
                                side_effect=socket.error),
              self.assertLogs(level="ERROR")
        ):
            core.send(self.command)
            wait_printer_cycles(2)
        self.assertEqual(core.writefailures, 1)


class TestListenThread(unittest.TestCase):
    """Functional checks for the listening thread"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def custom_slow_printer(self):
        """Simulate a slow processing printer"""
        time.sleep(CNC_PROCESS_TIME*random.randint(0, 90)/100)
        return self.printer_answer

    def setUp(self):
        self.printer_answer = DEFAULT_ANSWER.encode()
        self.mocked_serial = mock_serial(self, self.custom_slow_printer)
        self.core = printcore.printcore()
        self.mocked_handler = add_mocked_handler(self.core)
        self.recvcb = mock_callback(self, self.core, "recvcb")
        self.core.connect("/mocked/port", 1000)
        wait_printer_cycles(2)

    def test_handler_on_recv(self):
        """Test that the `on_recv` event is triggered"""
        event = self.mocked_handler.on_recv
        cb = self.recvcb
        subtest_mock(self, "", (event, cb), "assert_any_call", DEFAULT_ANSWER)

    def test_handler_on_temp(self):
        """Test that the `on_temp` event is triggered"""
        event = self.mocked_handler.on_temp
        cb = mock_callback(self, self.core, "tempcb")
        answer = f"{DEFAULT_ANSWER} T:"
        self.printer_answer = answer.encode()
        wait_printer_cycles(2)
        subtest_mock(self, "", (event, cb), "assert_any_call", answer)

    def test_read_resend(self):
        """Check resendfrom is set when resend is read"""
        self.printer_answer = "rs N2 Expected checksum 67".encode()
        wait_printer_cycles(2)
        self.assertEqual(self.core.resendfrom, 2)

    def test_read_none(self):
        """Test that an error is logged if None is read"""
        with self.assertLogs(level="ERROR"):
            self.printer_answer = None
            wait_printer_cycles(2)

    def test_read_bad_encoding(self):
        """Check that an error is logged on bad enconding"""
        with self.assertLogs(level="ERROR"):
            self.printer_answer = b'\xC0'
            wait_printer_cycles(2)

    def test_read_serial_error(self):
        """Check error is logged when serial error while reading"""
        with (
            self.assertLogs(level="ERROR"),
            mock.patch.object(self.mocked_serial.return_value, "readline",
                              side_effect=serial.SerialException)
        ):
            wait_printer_cycles(2)

    def test_calls_socket_read(self):
        """Test that socket file resource is read"""
        core, mocked_socket = setup_socket_core(self)
        socket_file = mocked_socket.return_value.makefile.return_value
        socket_file.read.assert_called()

    def test_read_socket_error(self):
        """Check error is logged when socket error while reading"""
        with (
            self.assertLogs(level="ERROR"),
            mock.patch.object(self.mocked_serial.return_value, "readline",
                              side_effect=socket.error)
        ):
            wait_printer_cycles(2)

    def test_read_error(self):
        """Test that an error is logged if 'Error' is read"""
        answer = "Error check."
        with self.assertLogs(level="ERROR"):
            self.printer_answer = answer.encode()
            wait_printer_cycles(2)

    def tearDown(self):
        self.printer_answer = DEFAULT_ANSWER.encode()
        wait_printer_cycles(2)
        self.core.disconnect()
