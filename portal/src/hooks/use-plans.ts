'use client'

import { useQuery } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

interface PlanTier {
  plan_type: string
  name: string
  description: string
  price_monthly: number | null
  price_annual: number | null
  price_unit?: string
  member_limit: number | null
  features: string[]
}

async function fetchPlans(): Promise<{ plans: PlanTier[] }> {
  const res = await fetch(`${API_BASE}/api/v1/billing/plans`)
  if (!res.ok) throw new Error('Failed to fetch plans')
  return res.json()
}

export function usePlans() {
  return useQuery({
    queryKey: ['plans'],
    queryFn: fetchPlans,
    staleTime: 1000 * 60 * 60, // Plans don't change often
  })
}
