#!/usr/bin/env python

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

import sys
import traceback
import logging
from printrun.pronsole import pronsole

if __name__ == "__main__":

    interp = pronsole()
    interp.parse_cmdline(sys.argv[1:])
    try:
        interp.cmdloop()
    except SystemExit:
        interp.p.disconnect()
    except:
        logging.error(_("Caught an exception, exiting:")
                      + "\n" + traceback.format_exc())
        interp.p.disconnect()
