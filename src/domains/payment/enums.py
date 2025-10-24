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


class SubscriptionPlan(str, Enum):
    """Subscription plan types"""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    INSTITUTION = "institution"


class SubscriptionStatus(str, Enum):
    """Subscription status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class RefundStatus(str, Enum):
    """Refund status"""

    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
