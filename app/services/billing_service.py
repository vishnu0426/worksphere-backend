"""
Billing service for subscription and payment management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
import uuid
import json

from app.models.billing import (
    Subscription, Invoice, InvoiceItem, Payment, BillingHistory,
    SubscriptionTier, SubscriptionStatus, PaymentStatus, InvoiceStatus
)
from app.models.user import User
from app.models.organization import Organization
from app.schemas.billing import (
    SubscriptionCreate, SubscriptionUpdate, PaymentCreate,
    SubscriptionTierInfo, UsageOverview
)


class BillingService:
    """Service for managing billing, subscriptions, and payments"""

    # Subscription tier configurations
    TIER_CONFIGS = {
        SubscriptionTier.FREE: {
            "name": "Free",
            "description": "Perfect for individuals and small teams getting started",
            "monthly_price": 0.0,
            "yearly_price": 0.0,
            "max_projects": 3,
            "max_team_members": 5,
            "max_storage_gb": 1,
            "max_api_calls": 1000,
            "features": [
                "Up to 3 projects",
                "Up to 5 team members",
                "1GB storage",
                "Basic project templates",
                "Email support"
            ]
        },
        SubscriptionTier.BASIC: {
            "name": "Basic",
            "description": "Great for growing teams with more projects",
            "monthly_price": 9.99,
            "yearly_price": 99.99,
            "max_projects": 10,
            "max_team_members": 15,
            "max_storage_gb": 10,
            "max_api_calls": 10000,
            "features": [
                "Up to 10 projects",
                "Up to 15 team members",
                "10GB storage",
                "Advanced project templates",
                "Priority email support",
                "Basic analytics"
            ]
        },
        SubscriptionTier.PREMIUM: {
            "name": "Premium",
            "description": "Perfect for established teams with advanced needs",
            "monthly_price": 29.99,
            "yearly_price": 299.99,
            "max_projects": 50,
            "max_team_members": 50,
            "max_storage_gb": 100,
            "max_api_calls": 50000,
            "features": [
                "Up to 50 projects",
                "Up to 50 team members",
                "100GB storage",
                "All project templates",
                "Priority support",
                "Advanced analytics",
                "Custom integrations",
                "API access"
            ]
        },
        SubscriptionTier.ENTERPRISE: {
            "name": "Enterprise",
            "description": "For large organizations with unlimited needs",
            "monthly_price": 99.99,
            "yearly_price": 999.99,
            "max_projects": None,
            "max_team_members": None,
            "max_storage_gb": 1000,
            "max_api_calls": None,
            "features": [
                "Unlimited projects",
                "Unlimited team members",
                "1TB storage",
                "All features included",
                "24/7 phone support",
                "Custom integrations",
                "Advanced security",
                "Dedicated account manager"
            ]
        }
    }

    @classmethod
    async def create_subscription(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        subscription_data: SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription for a user"""
        
        # Get tier configuration
        tier_config = cls.TIER_CONFIGS[subscription_data.tier]
        
        # Calculate period dates
        now = datetime.utcnow()
        if subscription_data.billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
            price = tier_config["yearly_price"]
        else:
            period_end = now + timedelta(days=30)
            price = tier_config["monthly_price"]
        
        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            organization_id=subscription_data.organization_id,
            tier=subscription_data.tier,
            status=SubscriptionStatus.ACTIVE,
            monthly_price=tier_config["monthly_price"],
            yearly_price=tier_config["yearly_price"],
            billing_cycle=subscription_data.billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
            next_billing_date=period_end,
            max_projects=tier_config["max_projects"],
            max_team_members=tier_config["max_team_members"],
            max_storage_gb=tier_config["max_storage_gb"],
            max_api_calls=tier_config["max_api_calls"]
        )
        
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        
        # Create billing history entry
        await cls.create_billing_history(
            db, user_id, subscription.id,
            "subscription_created",
            f"Subscription created for {subscription_data.tier.value} tier",
            price
        )
        
        # Generate first invoice
        await cls.generate_invoice(db, subscription.id)
        
        return subscription

    @classmethod
    async def update_subscription(
        cls,
        db: AsyncSession,
        subscription_id: uuid.UUID,
        update_data: SubscriptionUpdate
    ) -> Subscription:
        """Update an existing subscription"""
        
        # Get subscription
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Update fields
        if update_data.tier:
            tier_config = cls.TIER_CONFIGS[update_data.tier]
            subscription.tier = update_data.tier
            subscription.monthly_price = tier_config["monthly_price"]
            subscription.yearly_price = tier_config["yearly_price"]
            subscription.max_projects = tier_config["max_projects"]
            subscription.max_team_members = tier_config["max_team_members"]
            subscription.max_storage_gb = tier_config["max_storage_gb"]
            subscription.max_api_calls = tier_config["max_api_calls"]
        
        if update_data.billing_cycle:
            subscription.billing_cycle = update_data.billing_cycle
        
        if update_data.cancel_at_period_end is not None:
            subscription.cancel_at_period_end = update_data.cancel_at_period_end
            if update_data.cancel_at_period_end:
                subscription.cancelled_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(subscription)
        
        # Create billing history entry
        await cls.create_billing_history(
            db, subscription.user_id, subscription.id,
            "subscription_updated",
            f"Subscription updated to {subscription.tier.value} tier"
        )
        
        return subscription

    @classmethod
    async def cancel_subscription(
        cls,
        db: AsyncSession,
        subscription_id: uuid.UUID,
        immediate: bool = False
    ) -> Subscription:
        """Cancel a subscription"""
        
        # Get subscription
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")
        
        now = datetime.utcnow()
        
        if immediate:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = now
            subscription.current_period_end = now
        else:
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = now
        
        await db.commit()
        await db.refresh(subscription)
        
        # Create billing history entry
        await cls.create_billing_history(
            db, subscription.user_id, subscription.id,
            "subscription_cancelled",
            f"Subscription cancelled {'immediately' if immediate else 'at period end'}"
        )
        
        return subscription

    @classmethod
    async def generate_invoice(
        cls,
        db: AsyncSession,
        subscription_id: uuid.UUID
    ) -> Invoice:
        """Generate an invoice for a subscription"""
        
        # Get subscription
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Generate invoice number
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate amount
        if subscription.billing_cycle == "yearly":
            amount = subscription.yearly_price or 0.0
        else:
            amount = subscription.monthly_price or 0.0
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            subscription_id=subscription_id,
            user_id=subscription.user_id,
            status=InvoiceStatus.SENT if amount > 0 else InvoiceStatus.PAID,
            amount_subtotal=amount,
            amount_tax=0.0,  # TODO: Calculate tax based on location
            amount_total=amount,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            invoice_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=30),
            paid_date=datetime.utcnow() if amount == 0 else None,
            description=f"{cls.TIER_CONFIGS[subscription.tier]['name']} Plan - {subscription.billing_cycle.title()}"
        )
        
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        
        # Create invoice item
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            description=f"{cls.TIER_CONFIGS[subscription.tier]['name']} Plan ({subscription.billing_cycle})",
            quantity=1,
            unit_price=amount,
            amount=amount
        )
        
        db.add(invoice_item)
        await db.commit()
        
        return invoice

    @classmethod
    async def create_billing_history(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        subscription_id: Optional[uuid.UUID],
        event_type: str,
        description: str,
        amount: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BillingHistory:
        """Create a billing history entry"""
        
        history = BillingHistory(
            user_id=user_id,
            subscription_id=subscription_id,
            event_type=event_type,
            description=description,
            amount=amount,
            currency="USD" if amount else None,
            event_metadata=json.dumps(metadata) if metadata else None
        )
        
        db.add(history)
        await db.commit()
        await db.refresh(history)
        
        return history

    @classmethod
    def get_tier_info(cls, tier: SubscriptionTier) -> SubscriptionTierInfo:
        """Get information about a subscription tier"""
        config = cls.TIER_CONFIGS[tier]
        return SubscriptionTierInfo(
            tier=tier,
            **config
        )

    @classmethod
    def get_all_tier_info(cls) -> List[SubscriptionTierInfo]:
        """Get information about all subscription tiers"""
        return [cls.get_tier_info(tier) for tier in SubscriptionTier]
