import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000, // 2 min for large files
})

// ── Auto-attach Bearer token ──────────────────────
api.interceptors.request.use(config => {
  const token = localStorage.getItem('stamp_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Handle 401 → logout ──────────────────────────
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('stamp_token')
      // avoid reload loop on login page
      if (window.location.pathname !== '/' && !window.location.pathname.endsWith('/login')) {
        window.location.href = '/'
      }
    }
    return Promise.reject(err)
  }
)

/** Batch upload seals */
export function uploadSealsBatch(formData) {
  return api.post('/seals/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Upload a seal image */
export function uploadSeal(formData) {
  return api.post('/seals', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** List all seals */
export function listSeals(category) {
  return api.get('/seals', { params: { category } })
}

/** Delete a seal */
export function deleteSeal(id) {
  return api.delete(`/seals/${id}`)
}

/** Update seal metadata (seal_code, name, etc.) */
export function updateSeal(id, formData) {
  return api.patch(`/seals/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Get seal image URL */
export function getSealImageUrl(id) {
  return `/api/v1/seals/${id}/image`
}

/** Stamp a file */
export function stampFile(formData) {
  return api.post('/stamp', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
}

export default api
