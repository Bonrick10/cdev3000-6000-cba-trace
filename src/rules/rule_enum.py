""" Enum type for Rule violations  """ 

from enum import Enum

class RuleEnum(Enum):
    """ Enum for which rules have been violated """
    # Suspicious Rules 
    IMPOSSIBLE_TRAVEL = 1
    MERCHANT_TYPE_SUSPICIOUS_RANGE = 2
    # Unusual Rules 
    UNSEEN_DEVICE = 3
    EXCEED_7D_TOTAL = 4
    LARGE_AMOUNT_NEW_PAYEE = 5
    MERCHANT_TYPE_UNUSUAL_RANGE = 6
