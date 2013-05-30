""" CSS at-rules"""

from pyparsing import Literal, Combine
from .identifier import identifier

atkeyword = Combine(Literal("@") + identifier)