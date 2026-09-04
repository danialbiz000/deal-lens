/**
 * Shared fetch plumbing for lib/api.ts and lib/api-ai.ts -- split out purely
 * to keep each of those files under this project's 500-line limit, not for
 * any architectural reason (both files together are still "one thin fetch
 * client", per api.ts's own docstring).
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ? JSON.stringify(body.detail) : response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json() as Promise<T>;
}

export async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json() as Promise<T>;
}
