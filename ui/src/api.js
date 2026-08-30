/* Thin fetch wrapper. Errors carry the backend's `kind` so the UI can respond to
   a missing key differently from a missing consent, without string matching. */
export class ApiError extends Error {
  constructor(message, { kind = 'error', status = 0, retryable = false } = {}) {
    super(message);
    this.kind = kind;
    this.status = status;
    this.retryable = retryable;
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { error: text }; }
  if (!res.ok) {
    throw new ApiError((data && (data.error || data.detail)) || res.statusText, {
      kind: (data && data.kind) || 'error',
      status: res.status,
      retryable: Boolean(data && data.retryable),
    });
  }
  return data;
}
