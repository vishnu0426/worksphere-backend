"""
Billing and subscription schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from uuid import UUID

from app.models.billing import SubscriptionTier, SubscriptionStatus, PaymentStatus, InvoiceStatus


# Base schemas
class SubscriptionBase(BaseModel):
    tier: SubscriptionTier
    billing_cycle: str = "monthly"
    max_projects: Optional[int] = None
    max_team_members: Optional[int] = None
    max_storage_gb: Optional[int] = None
    max_api_calls: Optional[int] = None


class InvoiceItemBase(BaseModel):
    description: str
    quantity: int = 1
    unit_price: float
    amount: float


class PaymentBase(BaseModel):
    amount: float
    currency: str = "USD"
    payment_method: Optional[str] = None


# Request schemas
class SubscriptionCreate(SubscriptionBase):
    organization_id: Optional[UUID] = None


class SubscriptionUpdate(BaseModel):
    tier: Optional[SubscriptionTier] = None
    billing_cycle: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


class PaymentCreate(PaymentBase):
    payment_method_id: Optional[str] = None
    external_payment_intent_id: Optional[str] = None


class InvoiceItemCreate(InvoiceItemBase):
    pass


# Response schemas
class SubscriptionResponse(SubscriptionBase):
    id: UUID
    user_id: UUID
    organization_id: Optional[UUID]
    status: SubscriptionStatus
    monthly_price: float
    yearly_price: Optional[float]
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceItemResponse(InvoiceItemBase):
    id: UUID
    invoice_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    subscription_id: UUID
    user_id: UUID
    status: InvoiceStatus
    amount_subtotal: float
    amount_tax: float
    amount_total: float
    currency: str
    period_start: datetime
    period_end: datetime
    invoice_date: datetime
    due_date: datetime
    paid_date: Optional[datetime]
    pdf_url: Optional[str]
    pdf_generated_at: Optional[datetime]
    description: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    invoice_items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True


class PaymentResponse(PaymentBase):
    id: UUID
    subscription_id: UUID
    invoice_id: Optional[UUID]
    user_id: UUID
    status: PaymentStatus
    payment_method_id: Optional[str]
    external_payment_id: Optional[str]
    external_payment_intent_id: Optional[str]
    payment_date: Optional[datetime]
    failed_at: Optional[datetime]
    refunded_at: Optional[datetime]
    failure_reason: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillingHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    subscription_id: Optional[UUID]
    event_type: str
    description: str
    amount: Optional[float]
    currency: Optional[str]
    event_metadata: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Billing dashboard schemas
class UsageOverview(BaseModel):
    active_users: int
    max_users: int
    projects: int
    max_projects: int
    storage_gb: float
    max_storage_gb: int
    api_calls: int
    max_api_calls: int


class BillingDashboard(BaseModel):
    subscription: SubscriptionResponse
    usage: UsageOverview
    recent_invoices: List[InvoiceResponse]
    recent_payments: List[PaymentResponse]


# Subscription tier definitions
class SubscriptionTierInfo(BaseModel):
    tier: SubscriptionTier
    name: str
    description: str
    monthly_price: float
    yearly_price: float
    max_projects: Optional[int]
    max_team_members: Optional[int]
    max_storage_gb: Optional[int]
    max_api_calls: Optional[int]
    features: List[str]


class SubscriptionPlans(BaseModel):
    plans: List[SubscriptionTierInfo]


# PDF generation request
class GenerateInvoicePDFRequest(BaseModel):
    invoice_id: UUID


class GenerateInvoicePDFResponse(BaseModel):
    pdf_url: str
    generated_at: datetime


# Webhook schemas for payment processing
class PaymentWebhookData(BaseModel):
    external_payment_id: str
    status: PaymentStatus
    amount: float
    currency: str
    failure_reason: Optional[str] = None
    payment_date: Optional[datetime] = None


class PaymentWebhook(BaseModel):
    event_type: str
    data: PaymentWebhookData
    timestamp: datetime


# Validation
@validator('amount', 'unit_price', 'monthly_price', 'yearly_price', pre=True, always=True)
def validate_positive_amount(cls, v):
    if v is not None and v < 0:
        raise ValueError('Amount must be positive')
    return v


@validator('billing_cycle')
def validate_billing_cycle(cls, v):
    if v not in ['monthly', 'yearly']:
        raise ValueError('Billing cycle must be monthly or yearly')
    return v
