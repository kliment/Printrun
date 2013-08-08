#!/usr/bin/env python

import argparse

from printrun.prontserve import Prontserve

# Args
# -------------------------------------------------

if __name__ == "__main__":

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

if __name__ == "__main__":
  prontserve = Prontserve(dry_run=args.dry_run, loud=args.loud).start()
