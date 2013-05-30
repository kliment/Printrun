"""
    CSS blocks
"""

from pyparsing import nestedExpr

block = nestedExpr(opener="{", closer="}")

