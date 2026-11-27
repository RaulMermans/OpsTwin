function retryAfterMs(headers, attempt) {
  const raw = headers?.["retry-after"] ?? headers?.["Retry-After"];
  const seconds = Number(raw);
  if (Number.isFinite(seconds) && seconds >= 0) return Math.min(5000, seconds * 1000);
  return Math.min(5000, 250 * 2 ** attempt);
}

export async function fetchWithRetry(send, { maxRetries = 3, sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)) } = {}) {
  let attempt = 0;
  let retries = 0;
  let last;
  while (attempt <= maxRetries) {
    last = await send();
    if (last.status === 401 || last.status === 403) {
      return { ...last, retries, stopped: "authorization" };
    }
    if (last.status === 429 && attempt < maxRetries) {
      retries += 1;
      await sleep(retryAfterMs(last.headers, attempt));
      attempt += 1;
      continue;
    }
    if (last.status >= 500 && attempt < maxRetries) {
      retries += 1;
      await sleep(retryAfterMs(last.headers, attempt));
      attempt += 1;
      continue;
    }
    if (last.networkError && attempt < maxRetries) {
      retries += 1;
      await sleep(retryAfterMs(last.headers, attempt));
      attempt += 1;
      continue;
    }
    return { ...last, retries, stopped: last.status === 429 ? "retry_exhausted" : null };
  }
  return { ...last, retries, stopped: "retry_exhausted" };
}
