// Base URL 설정, fetch wrapper, 에러 파싱

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const BASE_URL = API_BASE_URL

export class ApiError extends Error {
  constructor(
    public status: number,
    public error: string,
    public detail?: string,
  ) {
    super(detail ?? error)
    this.name = 'ApiError'
  }
}

async function parseError(response: Response): Promise<never> {
  let body: { error?: string; detail?: string } = {}
  try {
    body = await response.json()
  } catch {
    // ignore parse error
  }
  throw new ApiError(
    response.status,
    body.error ?? response.statusText,
    body.detail,
  )
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const isFormData = options?.body instanceof FormData
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: isFormData
      ? { ...options?.headers }
      : { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    await parseError(response)
  }
  if (response.status === 204) {
    return undefined as unknown as T
  }
  return response.json() as Promise<T>
}

export function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: 'GET' })
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

export function apiPut<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function apiDelete(path: string): Promise<void> {
  return apiFetch<void>(path, { method: 'DELETE' })
}
