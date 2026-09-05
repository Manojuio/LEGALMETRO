const API_BASE = '/api/v1'

function getToken() {
  return localStorage.getItem('lm_token')
}

async function request(path, { method = 'GET', body, isForm = false } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (body && !isForm) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    localStorage.removeItem('lm_token')
    localStorage.removeItem('lm_user')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch (_) {}
    throw new Error(detail)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body }),
  patch: (p, body) => request(p, { method: 'PATCH', body }),
  delete: (p) => request(p, { method: 'DELETE' }),
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: { email, password } }),
  register: (payload) =>
    request('/auth/register', { method: 'POST', body: payload }),
  me: () => request('/auth/me'),
  dashboard: () => request('/dashboard/summary'),
  listUsers: () => request('/users'),
  lmos: () => request('/admins/lmos'),
  updateUser: (id, payload) => request(`/users/${id}`, { method: 'PATCH', body: payload }),
  products: () => request('/products'),
  createProduct: (payload) => request('/products', { method: 'POST', body: payload }),
  createAnalysis: (category) => {
    const fd = new FormData()
    fd.append('category', category)
    return request('/analyses', { method: 'POST', body: fd, isForm: true })
  },
  analyses: () => request('/analyses'),
  uploadImage: (analysisId, file, position) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('position', position)
    return request(`/analyses/${analysisId}/images`, { method: 'POST', body: fd, isForm: true })
  },
  runAnalysis: (analysisId) => request(`/analyses/${analysisId}/run`, { method: 'POST' }),
  getResult: (analysisId) => request(`/analyses/${analysisId}/result`),
  async downloadReport(analysisId) {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/report`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error('Could not fetch report')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `LegalMetriX_Inspection_${analysisId.slice(0, 8)}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
  inspections: () => request('/inspections'),
  createInspection: (payload) => request('/inspections', { method: 'POST', body: payload }),
  updateInspection: (id, payload) => request(`/inspections/${id}`, { method: 'PATCH', body: payload }),
  inspectionHistory: (statusFilter) => {
    const params = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ''
    return request(`/inspections/history${params}`)
  },
}
