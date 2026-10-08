// As rotas do sistema já começam com /api. Aceita tanto a URL antiga
// (https://servidor/api) quanto o novo proxy relativo (/api), sem duplicar.
const configuredApi = import.meta.env.VITE_API_URL
const API = configuredApi ? configuredApi.replace(/\/api\/?$/, '') : ''

function csrf(): string | undefined { return document.cookie.split('; ').find((item) => item.startsWith('csrf_token='))?.split('=')[1] }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? 'GET'
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
    const token = csrf(); if (token) headers.set('X-CSRF-Token', token)
  }
  const response = await fetch(`${API}${path}`, { ...init, method, headers, credentials: 'include' })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    const message = Array.isArray(detail)
      ? detail.map((item: { msg?: string }) => item.msg ?? 'Dados inválidos.').join(' ')
      : typeof detail === 'string' ? detail : 'Não foi possível concluir a operação.'
    throw new Error(message)
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
