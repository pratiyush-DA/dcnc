import axios from 'axios'

// In dev (Vite port 5173), use relative path so Vite proxy forwards /api -> backend:8000
const defaultBase =
  typeof window !== 'undefined' && window.location.port === '5173'
    ? '/api/v1'
    : 'http://localhost:8000/api/v1'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || defaultBase

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refreshToken')
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token } = response.data
          localStorage.setItem('accessToken', access_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`

          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export const authApi = {
  register: async (name: string, email: string, password: string, slug?: string) => {
    const response = await apiClient.post('/auth/register', {
      name,
      email,
      password,
      slug,
    })
    return response.data
  },

  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', {
      email,
      password,
    })
    return response.data
  },

  refreshToken: async (refresh_token: string) => {
    const response = await apiClient.post('/auth/refresh', {
      refresh_token,
    })
    return response.data
  },

  logout: async (refresh_token: string) => {
    const response = await apiClient.post('/auth/logout', {
      refresh_token,
    })
    return response.data
  },

  getMe: async () => {
    const response = await apiClient.get('/auth/me')
    return response.data
  },
}

export const classificationApi = {
  classify: async (file: File, options: any) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('has_header', String(options.has_header || true))
    formData.append('enable_validation', String(options.enable_validation || true))
    formData.append('enable_ml_clustering', String(options.enable_ml_clustering || true))
    formData.append('enable_ensemble_detection', String(options.enable_ensemble_detection || true))
    formData.append('strict_mode', String(options.strict_mode || false))

    const response = await apiClient.post('/classify/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

export const correctionApi = {
  classifyAndCorrect: async (file: File, options: any) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('has_header', String(options.has_header || true))
    formData.append('correction_threshold', String(options.correction_threshold || 0.7))
    formData.append('max_corrections_per_column', String(options.max_corrections_per_column || 1000))

    const response