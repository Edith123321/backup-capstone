// frontend_web/src/services/resilientFetch.js
/**
 * Cold-start-aware fetch wrapper.
 *
 * The backend runs on Render's free tier and spins down after ~15 min idle. The
 * first request then hits a booting container and Render's edge returns a 502
 * (with no CORS headers), which the browser reports as a confusing "CORS error".
 * This helper transparently retries on those transient failures (502/503/504 and
 * network errors) with backoff, and calls onRetry so the UI can say
 * "Waking up server…" instead of failing silently.
 */

export const API_BASE =
  import.meta.env.VITE_API_URL || 'https://capstone-be-yxzd.onrender.com';

const RETRYABLE_STATUS = new Set([502, 503, 504]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Fire-and-forget ping to wake the backend early (e.g. on dashboard load), so
 * it's warm by the time the nurse submits an encounter.
 */
export async function warmUpBackend() {
  try {
    await fetch(`${API_BASE}/api/v1/screening/health`, { method: 'GET', cache: 'no-store' });
    return true;
  } catch {
    return false;
  }
}

/**
 * fetch() with retry/backoff on cold-start failures.
 *
 * @param {string} url
 * @param {RequestInit} options
 * @param {object} cfg  { retries=3, backoffMs=2500, timeoutMs=90000, onRetry }
 *   onRetry(attempt, maxRetries) fires before each retry.
 * @returns {Promise<Response>}
 */
export async function resilientFetch(url, options = {}, cfg = {}) {
  const { retries = 3, backoffMs = 2500, timeoutMs = 90000, onRetry } = cfg;
  let lastError;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const resp = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timer);

      // Transient server/edge error (cold start) -> retry.
      if (RETRYABLE_STATUS.has(resp.status) && attempt < retries) {
        onRetry?.(attempt + 1, retries);
        await sleep(backoffMs * (attempt + 1));
        continue;
      }
      return resp;
    } catch (err) {
      clearTimeout(timer);
      lastError = err;
      // Network failure / timeout / connection reset while booting -> retry.
      if (attempt < retries) {
        onRetry?.(attempt + 1, retries);
        await sleep(backoffMs * (attempt + 1));
        continue;
      }
    }
  }
  throw lastError || new Error('Request failed after multiple attempts');
}

/**
 * Convenience: resilientFetch + JSON parse, throwing a friendly Error on failure.
 * Returns the parsed body on success (2xx) or throws with a human message.
 */
export async function resilientJson(url, options = {}, cfg = {}) {
  let resp;
  try {
    resp = await resilientFetch(url, options, cfg);
  } catch (err) {
    throw new Error(friendlyError(err));
  }
  let body = null;
  try { body = await resp.json(); } catch { /* non-JSON body */ }

  if (!resp.ok) {
    const msg = body?.error || body?.message || `Request failed (HTTP ${resp.status})`;
    throw new Error(msg);
  }
  return body;
}

/** Map a raw fetch error into a message a clinician can act on. */
export function friendlyError(err) {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return 'You appear to be offline. Your work will be saved locally and synced when the connection returns.';
  }
  if (err?.name === 'AbortError') {
    return 'The server took too long to respond — it may be waking up. Please try again.';
  }
  if (/failed to fetch|networkerror|load failed/i.test(err?.message || '')) {
    return 'Could not reach the server (it may be waking up after being idle). Please try again in a moment.';
  }
  return err?.message || 'Something went wrong. Please try again.';
}
