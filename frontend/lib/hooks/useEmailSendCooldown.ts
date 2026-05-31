"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/auth";

export function useEmailSendCooldown(defaultSeconds = 60) {
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  useEffect(() => {
    if (cooldownSeconds <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setCooldownSeconds((current) => (current <= 1 ? 0 : current - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldownSeconds]);

  function startCooldown(seconds: number) {
    setCooldownSeconds(Math.max(1, seconds));
  }

  function applyRateLimitError(error: unknown): string | null {
    if (error instanceof ApiError && error.status === 429) {
      startCooldown(error.retryAfterSeconds ?? defaultSeconds);
      return error.message;
    }
    return null;
  }

  return {
    cooldownSeconds,
    isOnCooldown: cooldownSeconds > 0,
    startCooldown,
    applyRateLimitError,
  };
}
