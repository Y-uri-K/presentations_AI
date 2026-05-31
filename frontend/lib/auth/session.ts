import { fetchMe, refreshAuthTokens } from "@/lib/api/auth";
import { isJwtExpired, isJwtExpiringSoon } from "@/lib/auth/jwt";
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "@/lib/auth/token";

let refreshInFlight: Promise<boolean> | null = null;

async function refreshSessionOnce(): Promise<boolean> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      return false;
    }

    try {
      const tokens = await refreshAuthTokens(refreshToken);
      saveTokens(tokens.access_token, tokens.refresh_token);
      return true;
    } catch {
      clearTokens();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

/** Проверяет access-токен, при необходимости обновляет пару JWT через refresh. */
export async function ensureValidSession(): Promise<boolean> {
  const accessToken = getAccessToken();
  const refreshToken = getRefreshToken();

  if (!accessToken && !refreshToken) {
    return false;
  }

  if (accessToken && !isJwtExpired(accessToken) && !isJwtExpiringSoon(accessToken)) {
    try {
      await fetchMe(accessToken);
      return true;
    } catch {
      // access отклонён — пробуем refresh
    }
  }

  if (!refreshToken) {
    clearTokens();
    return false;
  }

  const refreshed = await refreshSessionOnce();
  if (!refreshed) {
    return false;
  }

  const newAccess = getAccessToken();
  if (!newAccess) {
    return false;
  }

  try {
    await fetchMe(newAccess);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}
