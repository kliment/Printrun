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

import argparse

from printrun.prontserve import Prontserve

if __name__ == "__main__":
  # Args
  # -------------------------------------------------

  parser = argparse.ArgumentParser(
    description='Runs a 3D printer server using the Construct Protocol'
  )

  parser.add_argument('--dry-run', default=False, action='store_true',
    help='Does not connect to the 3D printer'
  )

  parser.add_argument('--loud', default=False, action='store_true',
    help='Enables verbose printer output'
  )

  parser.add_argument('--heaptrace', default=False, action='store_true',
    help='Enables a heap trace on exit (for developer use)'
  )

  args = parser.parse_args()

  # Server Start Up
  # -------------------------------------------------

  prontserve = Prontserve(**vars(args)).start()
