"""
Clean access control system integrating subscriptions and wallet.
"""

from src.domains.access_control.core import (
    AccessControl,
    AccessResult,
    AccessMethod,
)
from src.domains.access_control.decorators import (
    require_access,
    require_feature,
    require_subscription,
)
from src.domains.access_control.config import (
    AccessConfig,
    ResourceAccess,
    PricingTiers,
    FeatureCategories,
)
from src.domains.access_control.middleware import (
    AccessContextMiddleware,
    AccessContext,
    SubscriptionContext,
    WalletContext,
    get_access_context,
    require_subscription_context,
    require_wallet_context,
)

__all__ = [
    # Core
    "AccessControl",
    "AccessResult",
    "AccessMethod",
    # Decorators
    "require_access",
    "require_feature",
    "require_subscription",
    # Config
    "AccessConfig",
    "ResourceAccess",
    "PricingTiers",
    "FeatureCategories",
    # Middleware
    "AccessContextMiddleware",
    "AccessContext",
    "SubscriptionContext",
    "WalletContext",
    "get_access_context",
    "require_subscription_context",
    "require_wallet_context",
]
