'use client'

import { useQuery } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

interface SocialProofData {
  familyCount: number
  schoolCount: number
  countriesCount: number
}

const PLACEHOLDER: SocialProofData = {
  familyCount: 12000,
  schoolCount: 340,
  countriesCount: 28,
}

async function fetchSocialProof(): Promise<SocialProofData> {
  const res = await fetch(`${API_BASE}/api/v1/portal/social-proof`)
  if (!res.ok) {
    // Fall back to placeholder data if endpoint is unavailable
    return PLACEHOLDER
  }
  return res.json()
}

export function useSocialProof() {
  return useQuery({
    queryKey: ['social-proof'],
    queryFn: fetchSocialProof,
    staleTime: 1000 * 60 * 60, // 1 hour — social proof numbers update infrequently
    // Return placeholder data while loading so the UI is never empty
    placeholderData: PLACEHOLDER,
  })
}
