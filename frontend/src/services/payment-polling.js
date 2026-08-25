const MAX_DELAY_MS = 8_000;

export function paymentPollingDelay(attempt, retryAfterSeconds = null, random = Math.random) {
  const serverDelay = Number(retryAfterSeconds) * 1_000;
  const base = Number.isFinite(serverDelay) && serverDelay > 0
    ? serverDelay
    : Math.min(500 * (1.7 ** attempt), MAX_DELAY_MS);
  return Math.round(base * (0.75 + random() * 0.5));
}

export function abortableDelay(delayMs, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason || new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timerId = window.setTimeout(resolve, delayMs);
    signal?.addEventListener('abort', () => {
      window.clearTimeout(timerId);
      reject(signal.reason || new DOMException('Aborted', 'AbortError'));
    }, { once: true });
  });
}

export function waitForVisible(signal) {
  if (document.visibilityState !== 'hidden') return Promise.resolve();
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      signal?.removeEventListener('abort', onAbort);
    };
    const onVisibilityChange = () => {
      if (document.visibilityState !== 'hidden') {
        cleanup();
        resolve();
      }
    };
    const onAbort = () => {
      cleanup();
      reject(signal.reason || new DOMException('Aborted', 'AbortError'));
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

export function isAbortError(error) {
  return error?.name === 'AbortError';
}
