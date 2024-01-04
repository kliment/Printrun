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
#
# pylint: disable=unnecessary-pass
# pylint: disable=missing-function-docstring

class PrinterEventHandler:
    """Skeleton of an event-handler for printer events.

    It allows attaching to a printcore instance and the relevant method will
    be triggered for different events. See
    `printrun.printcore.printcore.addEventHandler`

    Event method `on_send` will be called at the same time and with the same
    arguments as the printcore `send` callback function. See
    `printrun.printcore.Callback`. Same logic applies to all other methods
    but for `on_preprintsend`, `on_init`, `on_connect` and
    `on_disconnect`. See below.

    """
    def __init__(self):
        """Event-handler constructor."""
        pass

    def on_init(self):
        """Called whenever a new printcore is initialized."""
        pass

    def on_send(self, command, gline):
        pass

    def on_recv(self, line):
        pass

    def on_connect(self):
        """Called whenever printcore is connected."""
        pass

    def on_disconnect(self):
        """Called whenever printcore is disconnected."""
        pass

    def on_error(self, error):
        pass

    def on_online(self):
        pass

    def on_temp(self, line):
        pass

    def on_start(self, resume):
        pass

    def on_end(self):
        pass

    def on_layerchange(self, layer):
        pass

    def on_preprintsend(self, gline, index, mainqueue):
        """Called before sending each command of a print.

        This event is only triggered on lines sent while a print is ongoing.
        See `printrun.printcore.printcore.startprint`.

        Parameters
        ----------
        gline : Line
            The `printrun.gcoder.Line` object containing the line of G-code to
            be sent.
        index : int
            Index of this `gline` within `mainqueue`.
        mainqueue : GCode
            A `printrun.gcoder.GCode` object with the current queue of
            commands being processed.
            See `printrun.printcore.printcore.mainqueue`.

        """
        # TODO[v3]: Rework to match callback function arguments?
        pass

    def on_printsend(self, gline):
        pass
