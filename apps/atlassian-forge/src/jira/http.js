function retryAfterMs(headers, attempt) {
  const raw = headers?.["retry-after"] ?? headers?.["Retry-After"];
  const seconds = Number(raw);
  if (Number.isFinite(seconds) && seconds >= 0) return seconds * 1000;
  return Math.min(5000, 250 * 2 ** attempt);
}

export async function fetchWithRetry(
  send,
  { maxRetries = 3, sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)), remainingMs } = {},
) {
  let attempt = 0;
  let retries = 0;
  let last;
  while (attempt <= maxRetries) {
    last = await send();
    if (last.status === 401 || last.status === 403) {
      return { ...last, retries, stopped: "authorization" };
    }
    const retryable = last.status === 429 || last.status >= 500 || last.networkError;
    if (retryable && attempt < maxRetries) {
      const delay = retryAfterMs(last.headers, attempt);
      if (typeof remainingMs === "number" && delay > remainingMs) {
        return { ...last, retries, stopped: "retry_exceeds_deadline" };
      }
      retries += 1;
      await sleep(delay);
      attempt += 1;
      continue;
    }
    return { ...last, retries, stopped: last.status === 429 ? "retry_exhausted" : null };
  }
  return { ...last, retries, stopped: "retry_exhausted" };
}
