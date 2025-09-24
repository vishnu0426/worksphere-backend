"""
Billing and subscription API endpoints
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
import uuid

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.billing import (
    Subscription, Invoice, Payment, BillingHistory,
    SubscriptionStatus, InvoiceStatus
)
from app.models.project import Project
from app.models.organization import OrganizationMember
from app.schemas.billing import (
    SubscriptionResponse, SubscriptionCreate, SubscriptionUpdate,
    InvoiceResponse, PaymentResponse, BillingHistoryResponse,
    BillingDashboard, UsageOverview, SubscriptionPlans,
    GenerateInvoicePDFRequest, GenerateInvoicePDFResponse
)
from app.services.billing_service import BillingService
from app.services.pdf_service import PDFInvoiceService

router = APIRouter()


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's subscription details"""
    
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED]))
        .order_by(desc(Subscription.created_at))
    )
    subscription = result.scalar_one_or_none()
    
    return subscription


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription"""
    
    # Check if user already has an active subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    existing_subscription = result.scalar_one_or_none()
    
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription"
        )
    
    subscription = await BillingService.create_subscription(
        db, current_user.id, subscription_data
    )
    
    return subscription


@router.put("/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    update_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current subscription"""
    
    # Get current subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    updated_subscription = await BillingService.update_subscription(
        db, subscription.id, update_data
    )
    
    return updated_subscription


@router.delete("/subscription", response_model=SubscriptionResponse)
async def cancel_subscription(
    immediate: bool = Query(False, description="Cancel immediately or at period end"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel current subscription"""
    
    # Get current subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    cancelled_subscription = await BillingService.cancel_subscription(
        db, subscription.id, immediate
    )
    
    return cancelled_subscription


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[InvoiceStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's invoice history"""
    
    query = select(Invoice).where(Invoice.user_id == current_user.id)
    
    if status:
        query = query.where(Invoice.status == status)
    
    query = query.options(selectinload(Invoice.invoice_items))
    query = query.order_by(desc(Invoice.created_at))
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific invoice details"""
    
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.user_id == current_user.id)
        .options(selectinload(Invoice.invoice_items))
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice


@router.post("/invoices/{invoice_id}/generate-pdf", response_model=GenerateInvoicePDFResponse)
async def generate_invoice_pdf(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate PDF for an invoice"""
    
    # Get invoice
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.user_id == current_user.id)
        .options(selectinload(Invoice.invoice_items))
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Generate PDF
    try:
        pdf_bytes = PDFInvoiceService.generate_invoice_pdf(
            invoice, current_user, invoice.invoice_items
        )

        # In a real implementation, you would save this to cloud storage (S3, etc.)
        # For now, we'll create a download URL
        pdf_url = f"/api/v1/billing/invoices/{invoice_id}/download"
        generated_at = datetime.utcnow()

        # Update invoice with PDF info
        invoice.pdf_url = pdf_url
        invoice.pdf_generated_at = generated_at
        await db.commit()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )
    
    return GenerateInvoicePDFResponse(
        pdf_url=pdf_url,
        generated_at=generated_at
    )


@router.get("/invoices/{invoice_id}/download")
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download invoice PDF"""

    # Get invoice
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.user_id == current_user.id)
        .options(selectinload(Invoice.invoice_items))
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    try:
        # Generate PDF
        pdf_bytes = PDFInvoiceService.generate_invoice_pdf(
            invoice, current_user, invoice.invoice_items
        )

        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/payment-history", response_model=List[PaymentResponse])
async def get_payment_history(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's payment history"""
    
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(desc(Payment.created_at))
        .offset(offset)
        .limit(limit)
    )
    payments = result.scalars().all()
    
    return payments


@router.get("/dashboard", response_model=BillingDashboard)
async def get_billing_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing dashboard data"""
    
    # Get current subscription
    subscription_result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED]))
        .order_by(desc(Subscription.created_at))
    )
    subscription = subscription_result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    # Get usage data
    # Count projects
    projects_result = await db.execute(
        select(func.count(Project.id))
        .where(Project.created_by == current_user.id)
    )
    project_count = projects_result.scalar() or 0
    
    # Count team members (organization members)
    members_result = await db.execute(
        select(func.count(OrganizationMember.id))
        .join(Subscription, Subscription.organization_id == OrganizationMember.organization_id)
        .where(Subscription.user_id == current_user.id)
    )
    member_count = members_result.scalar() or 1  # At least the user themselves
    
    # Create usage overview
    usage = UsageOverview(
        active_users=member_count,
        max_users=subscription.max_team_members or 999999,
        projects=project_count,
        max_projects=subscription.max_projects or 999999,
        storage_gb=0.0,  # TODO: Calculate actual storage usage
        max_storage_gb=subscription.max_storage_gb or 999999,
        api_calls=0,  # TODO: Calculate actual API usage
        max_api_calls=subscription.max_api_calls or 999999
    )
    
    # Get recent invoices
    invoices_result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == current_user.id)
        .options(selectinload(Invoice.invoice_items))
        .order_by(desc(Invoice.created_at))
        .limit(5)
    )
    recent_invoices = invoices_result.scalars().all()
    
    # Get recent payments
    payments_result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(desc(Payment.created_at))
        .limit(5)
    )
    recent_payments = payments_result.scalars().all()
    
    return BillingDashboard(
        subscription=subscription,
        usage=usage,
        recent_invoices=recent_invoices,
        recent_payments=recent_payments
    )


@router.get("/plans", response_model=SubscriptionPlans)
async def get_subscription_plans():
    """Get available subscription plans"""
    
    plans = BillingService.get_all_tier_info()
    return SubscriptionPlans(plans=plans)
