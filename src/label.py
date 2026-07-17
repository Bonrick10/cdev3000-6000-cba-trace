""" Enum type for labels  """ 

from enum import Enum

class Label(Enum):
    """ Enum to label transactions following SQL enums  """ 
    CONFIRMED_LEGITIMATE = 1
    LEGITIMATE = 2
    UNUSUAL = 3
    SUSPICIOUS = 4
    CONFIRMED_FRAUDULENT = 5
    RULE_VIOLATION = 6
