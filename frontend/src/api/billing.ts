/**
 * Billing API Client - Handles subscription tiers, credit balance, and checkout.
 */
import { apiClient, ApiResponse } from './client';

// ── Types ────────────────────────────────────────────────────────────

export interface TierInfo {
  tier: string;
  name: string;
  price_monthly: number;
  credits_monthly: number;
  daily_agent_limit: number;
  concurrent_agents: number;
  features: string[];
}

export interface CreditBalance {
  tier: string;
  tier_name: string;
  credits_remaining: number;
  credits_total: number;
  credits_used_today: number;
  credits_used_month: number;
  daily_agent_count: number;
  daily_agent_limit: number;
  stripe_customer_id: string | null;
}

export interface UsageStats {
  tier: string;
  credits_remaining: number;
  credits_total: number;
  credits_used_today: number;
  credits_used_month: number;
  daily_agent_count: number;
  daily_agent_limit: number;
  usage_percent: number;
}

export interface CreditCosts {
  agent_task: number;
  chat_message: number;
  image_generation: number;
  [key: string]: number;
}

// ── API Functions ────────────────────────────────────────────────────

/**
 * Get all available subscription tiers
 */
export async function getTiers(): Promise<TierInfo[]> {
  const response = await apiClient.get<ApiResponse<TierInfo[]>>('/billing/tiers');
  return response.data.data;
}

/**
 * Get credit costs per operation
 */
export async function getCreditCosts(): Promise<CreditCosts> {
  const response = await apiClient.get<ApiResponse<CreditCosts>>('/billing/credit-costs');
  return response.data.data;
}

/**
 * Get current user's credit balance
 */
export async function getBalance(): Promise<CreditBalance> {
  const response = await apiClient.get<ApiResponse<CreditBalance>>('/billing/balance');
  return response.data.data;
}

/**
 * Get usage statistics for dashboard
 */
export async function getUsageStats(): Promise<UsageStats> {
  const response = await apiClient.get<ApiResponse<UsageStats>>('/billing/usage');
  return response.data.data;
}

/**
 * Create a Stripe Checkout session
 */
export async function createCheckout(
  tier: string,
  successUrl: string,
  cancelUrl: string
): Promise<string> {
  const response = await apiClient.post<ApiResponse<{ checkout_url: string }>>('/billing/checkout', {
    tier,
    success_url: successUrl,
    cancel_url: cancelUrl,
  });
  return response.data.data.checkout_url;
}

/**
 * Create a Stripe Customer Portal session
 */
export async function createPortal(returnUrl: string): Promise<string> {
  const response = await apiClient.post<ApiResponse<{ portal_url: string }>>('/billing/portal', {
    return_url: returnUrl,
  });
  return response.data.data.portal_url;
}
