from fastapi import APIRouter

from src.domains.payment.api import transactions, subscriptions, wallet, refunds


payment_router = APIRouter()

# Include all sub-routers
payment_router.include_router(
    transactions.router, prefix="/transactions", tags=["Transactions"]
)

payment_router.include_router(
    subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"]
)

payment_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])

payment_router.include_router(refunds.router, prefix="/refunds", tags=["Refunds"])
