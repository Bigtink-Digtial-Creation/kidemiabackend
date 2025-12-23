from enum import Enum


class AccessMethod(str, Enum):
    """How user can access a resource"""

    SUBSCRIPTION = "subscription"
    WALLET = "wallet"
    FREE = "free"
    EITHER = "either"
