"use client";

import { useQuery } from "@tanstack/react-query";
import { billingApi, type CreditsBalance } from "@/lib/api";

/**
 * Credits balance with a 30s poll. react-query's refetchInterval handles the
 * timer + cleanup (the spec's "setInterval every 30s" without manual teardown).
 * Balance lives in query state, never localStorage.
 */
export function useCredits() {
  const query = useQuery<CreditsBalance>({
    queryKey: ["credits-balance"],
    queryFn: () => billingApi.creditsBalance().then((r) => r.data),
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    staleTime: 10_000,
    retry: false,
  });

  return {
    balance: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

/** Format eurocents as Dutch currency, e.g. 37500 → "€ 375,00". */
export function formatEuroCents(cents: number): string {
  return new Intl.NumberFormat("nl-NL", {
    style: "currency",
    currency: "EUR",
  }).format(cents / 100);
}

/** Whole euros without cents, e.g. 37500 → "€ 375". */
export function formatEuroWhole(cents: number): string {
  return new Intl.NumberFormat("nl-NL", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}
