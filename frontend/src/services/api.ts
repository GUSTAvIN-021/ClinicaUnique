// Em produção, a API é reescrita pelo Render em /api. Assim os cookies de
// sessão pertencem ao mesmo endereço do site e também funcionam no celular.
const API = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? '/api' : '')

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
