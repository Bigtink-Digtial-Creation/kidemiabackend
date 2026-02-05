from typing import Optional
from uuid import UUID
from decimal import Decimal
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

# Import your core logic and existing dependency providers
from src.domains.access_control.core import AccessControl, AccessResult
from src.core.security import get_current_user_id
from src.config.database import get_db


class RequireAccess:
    def __init__(
        self,
        resource: str,
        feature: Optional[str] = None,
        wallet_cost: Optional[Decimal] = None,
        activity_type: Optional[str] = None,
        auto_charge: bool = True,
        force_wallet: bool = False,
        feature_only: bool = False,
    ):
        self.resource = resource
        self.feature = feature
        self.wallet_cost = wallet_cost
        self.activity_type = activity_type
        self.auto_charge = auto_charge
        self.force_wallet = force_wallet
        self.feature_only = feature_only

    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db),
        current_user_id=Depends(get_current_user_id),
    ) -> AccessResult:
        if request.method == "OPTIONS":
            return AccessResult(
                allowed=True, method=None, reason="Preflight request - no charging"
            )
        # We pass the resolved 'db' into the Core here
        access_control = AccessControl(db)

        print("checkkkkkkkkkkkk")
        # SCENARIO A: Feature Only (No wallet fallback)
        if self.feature_only:
            access_result = await access_control._check_subscription_access(
                user_id=current_user_id,
                required_feature=self.feature,
                activity_type=self.activity_type,
            )

        # SCENARIO B: Wallet Only (Force skip subscription)
        elif self.force_wallet:
            if not self.wallet_cost:
                raise HTTPException(
                    status_code=500, detail="Wallet cost required for force_wallet"
                )
            access_result = await access_control._check_wallet_access(
                current_user_id, self.wallet_cost, self.resource
            )

        # SCENARIO C: Standard (Subscription with Wallet fallback)
        else:
            access_result = await access_control.check_access(
                user_id=current_user_id,
                resource=self.resource,
                required_feature=self.feature,
                wallet_cost=self.wallet_cost,
                activity_type=self.activity_type,
            )

        # Handle Denials
        if not access_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=access_result.to_dict(),
            )

        # Handle Execution (Charging)
        if self.auto_charge:
            # Try to find an ID in the path for activity tracking
            activity_id = (
                request.path_params.get("test_id")
                or request.path_params.get("id")
                or request.query_params.get("id")
            )

            # Convert string ID to UUID if present
            valid_uuid = None
            if activity_id:
                try:
                    valid_uuid = UUID(str(activity_id))
                except ValueError:
                    pass

            charged = await access_control.grant_access_and_charge(
                user_id=current_user_id,
                access_result=access_result,
                activity_type=self.activity_type or self.resource,
                activity_id=valid_uuid,
            )

            if not charged:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Access allowed but charging failed.",
                )

        return access_result
