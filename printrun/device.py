# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

# Standard libraries:
import os
import platform
import re
import selectors
import socket
import time

# Third-party libraries
import serial

READ_EMPTY = b''
"""Constant to represent empty or no data"""

READ_EOF = None
"""Constant to represent an end-of-file"""


class Device():
    """Handler for serial and web socket connections.

    Provides the same functions for both so it abstracts what kind of
    connection is being used.

    Parameters
    ----------
    port : str, optional
        Either a device name, such as '/dev/ttyUSB0' or 'COM3', or an URL with
        port, such as '192.168.0.10:80' or 'http://www.example.com:8080'.
    baudrate : int, optional
        Communication speed in bit/s, such as 9600, 115200 or 250000.
        (Default is 9600)
    force_dtr : bool or None, optional
        On serial connections, force the DTR bit to a specific logic level
        (1 or 0) after a successful connection. Not all OS/drivers support
        this functionality. By default it is set to "None" to let the system
        handle it automatically.
    parity_workaround : bool, optional
        On serial connections, enable/disable a workaround on parity
        checking. Not all platforms need to do this parity workaround, and
        some drivers don't support it. By default it is disabled.

    Attributes
    ----------
    is_connected
    has_flow_control

    """

    def __init__(self, port=None, baudrate=9600, force_dtr=None,
                 parity_workaround=False):
        self.port = port
        self.baudrate = baudrate
        self.force_dtr = force_dtr
        self.parity_workaround = parity_workaround

        # Private
        self._device = None
        self._is_connected = False
        self._hostname = None
        self._socketfile = None
        self._port_number = None
        self._read_buffer = []
        self._selector = None
        self._timeout = 0.25
        self._type = None

        if port is not None:
            self._parse_type()

    def connect(self, port=None, baudrate=None):
        """Establishes the connection to the device.

        Parameters
        ----------
        port : str, optional
            See `port` attribute. Only required if it was not provided
            already.
        baudrate : int, optional
            See `baudrate` attribute. Only required if it was not provided
            already.

        Raises
        ------
        DeviceError
            If an error occurred when attempting to connect.

        """
        if port is not None:
            self.port = port
        if baudrate is not None:
            self.baudrate = baudrate

        if self.port is not None:
            self._parse_type()
            getattr(self, "_connect_" + self._type)()
        else:
            raise DeviceError("No port or URL specified")

    def disconnect(self):
        """Terminates the connection to the device."""
        if self._device is not None:
            getattr(self, "_disconnect_" + self._type)()

    @property
    def is_connected(self):
        """True if connection to peer is alive.

        Warnings
        --------
        Current implementation for socket connections only tracks status of
        the connection but does not actually check it. So, if it is used to
        check the connection before sending data, it might fail to prevent an
        error being raised due to a lost connection.

        """
        if self._device is not None:
            return getattr(self, "_is_connected_" + self._type)()
        return False

    @property
    def has_flow_control(self):
        """True if the device has flow control mechanics."""
        if self._type == 'socket':
            return True
        return False

    def readline(self) -> bytes:
        """Read one line from the device stream.

        Returns
        -------
        bytes
            Array containing the feedback received from the
            device. `READ_EMPTY` will be returned if no data was
            available. `READ_EOF` is returned if connection was terminated at
            the other end.

        Raises
        ------
        DeviceError
            If connected peer is unreachable.

        """
        # TODO: silent fail on no device? return timeout?
        if self._device is not None:
            return getattr(self, "_readline_" + self._type)()
        raise DeviceError("Attempted to read when disconnected")

    def reset(self):
        """Attempt to reset the connection to the device.

        Warnings
        --------
        Current implementation has no effect on socket connections.

        """
        if self._device is not None:
            if self._type == 'serial':
                getattr(self, "_reset_" + self._type)()

    def write(self, data: bytes):
        """Write data to the connected peer.

        Parameters
        ----------
        data: bytes
            The bytes data to be written. This should be of type `bytes` (or
            compatible such as `bytearray` or `memoryview`). Unicode strings
            must be encoded.

        Raises
        ------
        DeviceError
            If connected peer is unreachable.
        TypeError
            If `data` is not of 'bytes' type.

        """
        if self._device is not None:
            getattr(self, "_write_" + self._type)(data)
        else:
            raise DeviceError("Attempted to write when disconnected")

    def _parse_type(self):
        # Guess which type of connection is being used
        if self._is_url(self.port):
            self._type = 'socket'
        else:
            self._type = 'serial'

    def _is_url(self, text):
        # TODO: Rearrange to avoid long line
        host_regexp = re.compile(r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$|^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$")
        if ':' in text:
            bits = text.split(":")
            if len(bits) == 2:
                self._hostname = bits[0]
                try:
                    self._port_number = int(bits[1])
                    if (host_regexp.match(self._hostname) and
                            1 <= self._port_number <= 65535):
                        return True
                except:
                    # TODO: avoid catch-all clauses
                    pass
        return False

    # ------------------------------------------------------------------------
    # Serial Functions
    # ------------------------------------------------------------------------
    def _connect_serial(self):
        # Disable HUPCL
        # TODO: Check if still required
        self._disable_ttyhup()

        try:
            # TODO: Check if this trick is still needed
            if self.parity_workaround:
                self._device = serial.Serial(port=self.port,
                                             baudrate=self.baudrate,
                                             timeout=0.25,
                                             parity=serial.PARITY_ODD)
                self._device.close()
                self._device.parity = serial.PARITY_NONE
            else:
                self._device = serial.Serial(baudrate=self.baudrate,
                                             timeout=0.25,
                                             parity=serial.PARITY_NONE)
                self._device.port = self.port

            # TODO: Check if this is still required
            if self.force_dtr is not None:
                self._device.dtr = self.force_dtr

            self._device.open()

        except (serial.SerialException, IOError) as e:
            msg = "Could not connect to serial port '{}'".format(self.port)
            raise DeviceError(msg, e) from e

    def _is_connected_serial(self):
        return self._device.is_open

    def _disconnect_serial(self):
        try:
            self._device.close()
        except serial.SerialException as e:
            msg = "Error on serial disconnection"
            raise DeviceError(msg, e) from e

    def _readline_serial(self):
        try:
            # Serial.readline() returns b'' (aka `READ_EMPTY`) on timeout
            return self._device.readline()
        except (serial.SerialException, OSError) as e:
            msg = f"Unable to read from serial port '{self.port}'"
            raise DeviceError(msg, e) from e

    def _reset_serial(self):
        self._device.dtr = True
        time.sleep(0.2)
        self._device.dtr = False

    def _write_serial(self, data):
        try:
            self._device.write(data)
        except serial.SerialException as e:
            msg = f"Unable to write to serial port '{self.port}'"
            raise DeviceError(msg, e) from e

    def _disable_ttyhup(self):
        if platform.system() == "Linux":
            os.system("stty -F %s -hup" % self.port)

    # ------------------------------------------------------------------------
    # Socket Functions
    # ------------------------------------------------------------------------
    def _connect_socket(self):
        self._device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._timeout = 0.25
        self._device.settimeout(1.0)

        try:
            self._device.connect((self._hostname, self._port_number))
            # A single read timeout raises OSError for all later reads
            # probably since python 3.5 use non blocking instead
            self._device.settimeout(0)
            self._socketfile = self._device.makefile('rwb', buffering=0)
            self._selector = selectors.DefaultSelector()
            self._selector.register(self._device, selectors.EVENT_READ)
            self._is_connected = True

        except OSError as e:
            self._disconnect_socket()
            msg = "Could not connect to {}:{}".format(self._hostname,
                                                      self._port_number)
            raise DeviceError(msg, e) from e

    def _is_connected_socket(self):
        # TODO: current implementation tracks status of connection but
        # does not actually check it. Ref. is_connected()
        return self._is_connected

    def _disconnect_socket(self):
        self._is_connected = False
        try:
            if self._socketfile is not None:
                self._socketfile.close()
            if self._selector is not None:
                self._selector.unregister(self._device)
                self._selector.close()
                self._selector = None
            self._device.close()
        except OSError as e:
            msg = "Error on socket disconnection"
            raise DeviceError(msg, e) from e

    def _readline_socket(self):
        SYS_AGAIN = None  # python's marker for timeout/no data
        # SYS_EOF = b''   # python's marker for EOF
        try:
            line = self._readline_buf()
            if line:
                return line
            chunk_size = 256
            while True:
                chunk = self._socketfile.read(chunk_size)
                if (chunk is SYS_AGAIN and
                        self._selector.select(self._timeout)):
                    chunk = self._socketfile.read(chunk_size)
                if chunk:
                    self._read_buffer.append(chunk)
                    line = self._readline_buf()
                    if line:
                        return line
                elif chunk is SYS_AGAIN:
                    return READ_EMPTY
                else:  # chunk is SYS_EOF
                    line = b''.join(self._read_buffer)
                    self._read_buffer = []
                    if line:
                        return line
                    self._is_connected = False
                    return READ_EOF
        except OSError as e:
            self._is_connected = False
            msg = ("Unable to read from {}:{}. Connection lost"
                   ).format(self._hostname, self._port_number)
            raise DeviceError(msg, e) from e

    def _readline_buf(self):
        # Try to readline from buffer
        if self._read_buffer:
            chunk = self._read_buffer[-1]
            eol = chunk.find(b'\n')
            if eol >= 0:
                line = b''.join(self._read_buffer[:-1]) + chunk[:(eol+1)]
                self._read_buffer = []
                if eol + 1 < len(chunk):
                    self._read_buffer.append(chunk[(eol+1):])
                return line
        return READ_EMPTY

    def _write_socket(self, data):
        try:
            self._socketfile.write(data)
            try:
                self._socketfile.flush()
            except socket.timeout:
                pass
        except (OSError, RuntimeError) as e:
            self._is_connected = False
            msg = ("Unable to write to {}:{}. Connection lost"
                   ).format(self._hostname, self._port_number)
            raise DeviceError(msg, e) from e


class DeviceError(Exception):
    """Raised on any connection error.

    One exception groups all connection errors regardless of the underlying
    connection or error type.

    Parameters
    ----------
    msg : str
        Error message.
    cause : Exception, optional
        Underlying error.

    Attributes
    ----------
    cause

    """

    def __init__(self, msg, cause=None):
        super().__init__(msg)
        self.cause = cause
