-- Migration: Add billing and subscription tables
-- Date: 2025-09-22
-- Description: Add comprehensive billing system with subscriptions, invoices, payments, and billing history

-- Create subscription tier enum
CREATE TYPE subscription_tier AS ENUM ('free', 'basic', 'premium', 'enterprise');

-- Create subscription status enum
CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'expired', 'pending', 'suspended');

-- Create payment status enum
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded', 'cancelled');

-- Create invoice status enum
CREATE TYPE invoice_status AS ENUM ('draft', 'sent', 'paid', 'overdue', 'cancelled');

-- Create subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    
    -- Subscription details
    tier subscription_tier NOT NULL DEFAULT 'free',
    status subscription_status NOT NULL DEFAULT 'active',
    
    -- Pricing
    monthly_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    yearly_price DECIMAL(10,2),
    billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',
    
    -- Billing dates
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end TIMESTAMPTZ NOT NULL,
    next_billing_date TIMESTAMPTZ,
    
    -- Subscription lifecycle
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Limits and features
    max_projects INTEGER,
    max_team_members INTEGER,
    max_storage_gb INTEGER,
    max_api_calls INTEGER,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create invoices table
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Invoice details
    status invoice_status NOT NULL DEFAULT 'draft',
    amount_subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    amount_tax DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    amount_total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Billing period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Dates
    invoice_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_date TIMESTAMPTZ NOT NULL,
    paid_date TIMESTAMPTZ,
    
    -- PDF storage
    pdf_url VARCHAR(500),
    pdf_generated_at TIMESTAMPTZ,
    
    -- Metadata
    description TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create invoice_items table
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    
    -- Item details
    description VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Payment details
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status payment_status NOT NULL DEFAULT 'pending',
    
    -- Payment method
    payment_method VARCHAR(50),
    payment_method_id VARCHAR(100),
    
    -- External payment provider data
    external_payment_id VARCHAR(100),
    external_payment_intent_id VARCHAR(100),
    
    -- Dates
    payment_date TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    
    -- Metadata
    failure_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create billing_history table
CREATE TABLE billing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    
    -- Related data
    amount DECIMAL(10,2),
    currency VARCHAR(3),
    
    -- Metadata
    event_metadata TEXT, -- JSON string for additional data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_organization_id ON subscriptions(organization_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_tier ON subscriptions(tier);
CREATE INDEX idx_subscriptions_next_billing_date ON subscriptions(next_billing_date);

CREATE INDEX idx_invoices_subscription_id ON invoices(subscription_id);
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);

CREATE INDEX idx_invoice_items_invoice_id ON invoice_items(invoice_id);

CREATE INDEX idx_payments_subscription_id ON payments(subscription_id);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_external_payment_id ON payments(external_payment_id);

CREATE INDEX idx_billing_history_user_id ON billing_history(user_id);
CREATE INDEX idx_billing_history_subscription_id ON billing_history(subscription_id);
CREATE INDEX idx_billing_history_event_type ON billing_history(event_type);
CREATE INDEX idx_billing_history_created_at ON billing_history(created_at);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default free subscription for existing users
INSERT INTO subscriptions (user_id, tier, status, monthly_price, yearly_price, billing_cycle, current_period_start, current_period_end, next_billing_date, max_projects, max_team_members, max_storage_gb, max_api_calls)
SELECT 
    id as user_id,
    'free' as tier,
    'active' as status,
    0.00 as monthly_price,
    0.00 as yearly_price,
    'monthly' as billing_cycle,
    NOW() as current_period_start,
    NOW() + INTERVAL '30 days' as current_period_end,
    NOW() + INTERVAL '30 days' as next_billing_date,
    3 as max_projects,
    5 as max_team_members,
    1 as max_storage_gb,
    1000 as max_api_calls
FROM users
WHERE NOT EXISTS (
    SELECT 1 FROM subscriptions WHERE subscriptions.user_id = users.id
);

-- Create billing history entries for the default subscriptions
INSERT INTO billing_history (user_id, subscription_id, event_type, description, amount, currency)
SELECT 
    s.user_id,
    s.id as subscription_id,
    'subscription_created' as event_type,
    'Default free subscription created during migration' as description,
    0.00 as amount,
    'USD' as currency
FROM subscriptions s
WHERE s.tier = 'free' AND s.created_at >= NOW() - INTERVAL '1 minute';

COMMIT;
