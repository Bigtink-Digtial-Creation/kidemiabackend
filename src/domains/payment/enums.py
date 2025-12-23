from enum import Enum


class TransactionType(str, Enum):
    """Type of transaction"""

    EXAM_PURCHASE = "exam_purchase"
    SUBSCRIPTION = "subscription"
    WALLET_TOPUP = "wallet_topup"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"
    COMMISSION = "commission"


class TransactionStatus(str, Enum):
    """Transaction status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment methods"""

    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    USSD = "ussd"
    WALLET = "wallet"
    PAYSTACK = "paystack"
    STRIPE = "stripe"
    FLUTTERWAVE = "flutterwave"


class PaymentGateway(str, Enum):
    """Payment gateway providers"""

    PAYSTACK = "paystack"
    STRIPE = "stripe"
    FLUTTERWAVE = "flutterwave"
    INTERNAL = "internal"  # For wallet transactions


class SubscriptionPlanType(str, Enum):
    """Plan types that can be created (for SubscriptionPlanConfig)"""

    FREE = "free"
    STUDENT = "student"
    SIBLING = "sibling"
    FAMILY = "family"
    INSTITUTION = "institution"
    CUSTOM = "custom"


class SubscriptionType(str, Enum):
    """Subscription type for grouping"""

    INDIVIDUAL = "individual"
    FAMILY = "family"
    INSTITUTION = "institution"


class SubscriptionStatus(str, Enum):
    """Subscription status"""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    PENDING = "pending"
    TRIAL = "trial"


class MemberRole(str, Enum):
    """Role of subscription member"""

    OWNER = "owner"
    MEMBER = "member"
    WARD = "ward"
    STUDENT = "student"


class BillingCycle(str, Enum):
    """Billing cycle options"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PromotionStatus(str, Enum):
    """Promotion status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"  # Max uses reached


class RefundStatus(str, Enum):
    """Refund status"""

    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
