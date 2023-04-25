"""Test suite for `printrun/device.py`"""
# How to run the tests (requires Python 3.11+):
#   python3 -m unittest discover tests

# Standard libraries:
import socket
import unittest
from unittest import mock

# Third-party libraries:
import serial

# Custom libraries:
# pylint: disable-next=no-name-in-module
from printrun import device


def mock_sttyhup(cls):
    """Fake stty control"""
    # Needed to avoid error:
    # "stty: /mocked/port: No such file or directory"
    cls.enterClassContext(
        mock.patch("printrun.device.Device._disable_ttyhup"))


def patch_serial(function, **kwargs):
    """Patch a function of serial.Serial"""
    return mock.patch(f"serial.Serial.{function}", **kwargs)


def patch_serial_is_open():
    """Patch the serial.Serial class and make `is_open` always True"""
    class_mock = mock.create_autospec(serial.Serial)
    instance_mock = class_mock.return_value
    instance_mock.is_open = True
    return mock.patch("serial.Serial", class_mock)


def patch_socket(function, **kwargs):
    """Patch a function of socket.socket"""
    return mock.patch(f"socket.socket.{function}", **kwargs)


def patch_socketio(function, **kwargs):
    """Patch a function of socket.SocketIO"""
    return mock.patch(f"socket.SocketIO.{function}", **kwargs)


def setup_serial(test):
    """Set up a Device through a mocked serial connection"""
    dev = device.Device()
    test.addCleanup(dev.disconnect)
    mocked_open = test.enterContext(patch_serial("open"))
    dev.connect("/mocked/port")

    return dev, mocked_open


def setup_socket(test):
    """Set up a Device through a mocked socket connection"""
    dev = device.Device()
    test.addCleanup(dev.disconnect)
    mocked_socket = test.enterContext(patch_socket("connect"))
    dev.connect("127.0.0.1:80")

    return dev, mocked_socket


class TestInit(unittest.TestCase):
    """Test Device constructor"""

    def test_type_serial(self):
        """Check detecting serial devices"""
        dev = device.Device("/any/port")

        with self.subTest("`serial` type is set"):
            # pylint: disable-next=protected-access
            self.assertEqual(dev._type, "serial")

        with self.subTest("No flow control is set"):
            self.assertFalse(dev.has_flow_control)

    def test_type_socket(self):
        """Check detecting socket devices"""
        dev = device.Device("127.0.0.1:80")

        with self.subTest("Check `socket` type is set"):
            # pylint: disable-next=protected-access
            self.assertEqual(dev._type, "socket")

        with self.subTest("Check flow control is set"):
            self.assertTrue(dev.has_flow_control)

    def test_default_type(self):
        """`serial` type is assigned by default when type unknown"""
        # If URL cannot be identified, a serial port is assumed
        dev = device.Device("/any/port:")
        # pylint: disable-next=protected-access
        self.assertEqual(dev._type, "serial")


class TestDisconnect(unittest.TestCase):
    """Test disconnect functionality"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def test_silent_on_no_device(self):
        """No error is raised when disconnecting a device not connected"""
        dev = device.Device()
        dev.disconnect()

    def test_socket_erorr(self):
        """DeviceError is raised if socket fails at disconnect"""
        dev, _ = setup_socket(self)
        with mock.patch('socket.socket.close', side_effect=socket.error):
            with self.assertRaises(device.DeviceError):
                dev.disconnect()

    def test_serial_erorr(self):
        """DeviceError is raised if serial fails at disconnect"""
        dev, _ = setup_serial(self)
        with patch_serial("close", side_effect=serial.SerialException):
            with self.assertRaises(device.DeviceError):
                dev.disconnect()


class TestConnect(unittest.TestCase):
    """Test connect functionality"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.dev = device.Device()
        self.addCleanup(self.dev.disconnect)

    def _fake_serial_connect(self, port=None, baudrate=None, dtr=None,
                             **kargs):
        # Mock a serial connection with optional keyword arguments
        with patch_serial("open", **kargs) as mocked_open:
            self.dev.connect(port=port, baudrate=baudrate, dtr=dtr)
            mocked_open.assert_called_once()

    def _fake_socket_connect(self, port=None, **kargs):
        # Mock a socket connection with optional keyword arguments
        with patch_socket("connect", **kargs) as mocked_connect:
            self.dev.connect(port)
            mocked_connect.assert_called_once()

    def test_error_on_no_device(self):
        """DeviceError is raised when connecting to no port/URL"""
        with self.assertRaises(device.DeviceError):
            self.dev.connect()
        self.assertFalse(self.dev.is_connected)

    def test_erorr_on_bad_port(self):
        """DeviceError is raised when port does not exist"""
        # Serial raises a FileNotFoundError
        with self.assertRaises(device.DeviceError):
            self.dev.connect("/non/existent/port")
        self.assertFalse(self.dev.is_connected)

    def test_call_socket_connect(self):
        """socket.socket.connect is called and `is_connected` is set"""
        self._fake_socket_connect("127.0.0.1:80")
        self.assertTrue(self.dev.is_connected)

    def test_call_serial_open(self):
        """serial.Serial.open is called and `is_connected` is set"""
        with patch_serial_is_open() as mocked_serial:
            self.dev.connect("/mocked/port")
            mocked_serial.return_value.open.assert_called_once()
            self.assertTrue(self.dev.is_connected)

    def test_set_baudrate(self):
        """Successful connection sets `port` and `baudrate`"""
        self._fake_serial_connect("/mocked/port", 250000)
        self.assertTrue(self.dev.port == "/mocked/port")
        self.assertTrue(self.dev.baudrate == 250000)

    def test_set_dtr(self):
        """Test no error raised on setting DTR on connect"""
        self._fake_serial_connect("/mocked/port", dtr=True)

    def test_connect_already_connected(self):
        """Test connecting an already connected device"""
        self._fake_serial_connect("/mocked/port")
        self._fake_serial_connect("/mocked/port2")
        self.assertTrue(self.dev.port == "/mocked/port2")

    def test_connect_serial_to_socket(self):
        """Test connecting from a port to a socket"""
        # pylint: disable=protected-access
        self._fake_serial_connect("/mocked/port")
        self.assertEqual(self.dev._type, "serial")
        self._fake_socket_connect("127.0.0.1:80")
        self.assertEqual(self.dev._type, "socket")

    def test_socket_error(self):
        """DeviceError is raised on socket.error on connect"""
        with self.assertRaises(device.DeviceError):
            self._fake_socket_connect("127.0.0.1:80", side_effect=socket.error)
        self.assertFalse(self.dev.is_connected)


class TestReset(unittest.TestCase):
    """Test reset functionality"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.serial_dev, _ = setup_serial(self)
        self.socket_dev, _ = setup_socket(self)

    def test_reset_serial(self):
        # TODO: this simply tests that no errors are raised
        self.serial_dev.reset()

    def test_reset_socket(self):
        # TODO: this simply tests that no errors are raised
        self.socket_dev.reset()


class TestReadSerial(unittest.TestCase):
    """Test readline functionality on serial connections"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.dev, _ = setup_serial(self)

    def _fake_read(self, **kargs):
        # Allows mocking a serial read operation for different return values
        with patch_serial("readline", **kargs) as mocked_read:
            data = self.dev.readline()
            mocked_read.assert_called_once()
            return data

    def test_calls_readline(self):
        """serial.Serial.readline is called"""
        self._fake_read()

    def test_read_data(self):
        """Data returned by serial.Serial.readline is passed as is"""
        data = self._fake_read(return_value=b"data\n")
        self.assertEqual(data, b"data\n")

    def test_read_serial_exception(self):
        """DeviceError is raised on serial error during reading"""
        with self.assertRaises(device.DeviceError):
            self._fake_read(side_effect=serial.SerialException)

    def test_read_empty(self):
        """READ_EMPTY is returned when there's nothing to read"""
        # Serial.readline() returns b'' (aka `READ_EMPTY`) on timeout
        self.assertEqual(self._fake_read(return_value=b''), device.READ_EMPTY)


class TestReadSocket(unittest.TestCase):
    """Test readline functionality on socket connections"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.dev, _ = setup_socket(self)

    def _fake_read(self, **kargs):
        with patch_socketio("read", **kargs) as mocked_read:
            data = self.dev.readline()
            mocked_read.assert_called()
            return data

    def test_read_empty(self):
        """READ_EMPTY is returned when there's nothing to read"""
        # If the socket is non-blocking and no bytes are available,
        # None is returned by readinto()
        # Device remains connected in this scenario
        data = self._fake_read(return_value=None)
        self.assertEqual(data, device.READ_EMPTY)
        self.assertTrue(self.dev.is_connected)

    def test_read_eof(self):
        """READ_EOF is returned when connection is terminated"""
        # A 0 return value from readinto() indicates that the
        # connection was shutdown at the other end
        # Device is no longer connected in this scenario
        data = self._fake_read(return_value=0)
        self.assertEqual(data, device.READ_EOF)
        self.assertFalse(self.dev.is_connected)

    def test_read_no_endpoint(self):
        """DeviceError is raised when connection is lost"""
        # OSError: [Errno 107] Transport endpoint is not connected
        # Thrown when trying to read but connection was lost
        with self.assertRaises(device.DeviceError):
            self.dev.readline()
        self.assertFalse(self.dev.is_connected)

    def test_read_data(self):
        """Data returned by socket.socket.read is passed as is"""
        with mock.patch('socket.SocketIO.read', return_value=b"data\n"):
            self.assertEqual(self.dev.readline(), b"data\n")


class TestWriteSerial(unittest.TestCase):
    """Test write functionality on serial connections"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def _setup_serial_write(self, side_effect=None):
        # Set up a mocked serial with optional side effects for the
        # serial.Serial.write function
        class_mock = mock.create_autospec(serial.Serial)
        instance_mock = class_mock.return_value
        instance_mock.is_open = True
        if side_effect is not None:
            instance_mock.write.side_effect = side_effect
        mocked_serial = self.enterContext(mock.patch("serial.Serial",
                                                     class_mock))

        dev = device.Device()
        self.addCleanup(dev.disconnect)
        dev.connect("/mocked/port")

        return dev, mocked_serial

    def test_write_no_device(self):
        """DeviceError is raised when device is not connected"""
        # This test serves for socket connections as well, this functionality
        # is independent of the underlying connection type
        empty_dev = device.Device()
        with self.assertRaises(device.DeviceError):
            empty_dev.write("test")

    def test_calls_serial_write(self):
        """serial.Serial.write is called"""
        dev, mocked_serial = self._setup_serial_write()
        dev.write("test")
        mocked_serial.return_value.write.assert_called_once_with("test")

    def test_write_serial_error(self):
        """DeviceError is raised on serial error during writing"""
        dev, _ = self._setup_serial_write(serial.SerialException)
        with self.assertRaises(device.DeviceError):
            dev.write("test")


class TestWriteSocket(unittest.TestCase):
    """Test write functionality on socket connections"""

    @classmethod
    def setUpClass(cls):
        mock_sttyhup(cls)

    def setUp(self):
        self.dev, _ = setup_socket(self)

    def _fake_write(self, data, **kwargs):
        # Perform a fake write operation. `kwargs` allows to set different
        # return values for the write operation
        with patch_socketio("write", **kwargs) as mocked_write:
            self.dev.write(data)
            mocked_write.assert_called_once_with(data)

    def test_calls_socket_write(self):
        """socket.socket.write is called"""
        self._fake_write(b"test")

    def test_write_errors(self):
        """DeviceError is raised on socket errors during writing"""
        # On errors during writing, the function is expected to raise a
        # DeviceError and terminate the connection
        self.assertTrue(self.dev.is_connected)
        for e in [OSError, RuntimeError]:
            with self.subTest(error=e):
                with self.assertRaises(device.DeviceError):
                    self._fake_write(b"test", side_effect=e)
                self.assertFalse(self.dev.is_connected)

    def test_not_bytes(self):
        """TypeError is raised if argument is not of bytes type"""
        with self.assertRaises(TypeError):
            self.dev.write("string")

    def test_flush_timeout(self):
        """Silent on socket timeout during flushing"""
        # Current behavior is to silently ignore socket.timeout
        with mock.patch('socket.SocketIO.flush', side_effect=socket.timeout):
            self._fake_write(b"test")
