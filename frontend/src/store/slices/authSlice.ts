import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { authApi } from '../../services/api'

/** Parse FastAPI/Pydantic 422 validation error: { detail: [{ msg }, ...] } or { detail: "string" } */
function getMessageFromApiError(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return ''
  const detail = (payload as { detail?: unknown }).detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d: { msg?: string; message?: string }) => d?.msg ?? d?.message)
      .filter(Boolean) as string[]
    return messages.join('. ')
  }
  if (typeof detail === 'string') return detail
  return ''
}

interface AuthState {
  user: {
    id: string
    email: string
    role: string
    client_id: string
  } | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
  isAuthenticated: !!localStorage.getItem('accessToken'),
  loading: false,
  error: null,
}

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await authApi.login(credentials.email, credentials.password)
      return response
    } catch (err: unknown) {
      const data = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: unknown } }).response?.data
        : undefined
      return rejectWithValue(data)
    }
  }
)

export const register = createAsyncThunk(
  'auth/register',
  async (
    data: { name: string; email: string; password: string; slug?: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await authApi.register(data.name, data.email, data.password, data.slug)
      return response
    } catch (err: unknown) {
      const data = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: unknown } }).response?.data
        : undefined
      return rejectWithValue(data)
    }
  }
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null
      state.accessToken = null
      state.refreshToken = null
      state.isAuthenticated = false
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload.user
        state.accessToken = action.payload.tokens.access_token
        state.refreshToken = action.payload.tokens.refresh_token
        state.isAuthenticated = true
        localStorage.setItem('accessToken', action.payload.tokens.access_token)
        localStorage.setItem('refreshToken', action.payload.tokens.refresh_token)
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false
        state.error =
          getMessageFromApiError(action.payload) ||
          action.error.message ||
          'Login failed'
      })
      .addCase(register.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(register.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload.user
        state.accessToken = action.payload.tokens.access_token
        state.refreshToken = action.payload.tokens.refresh_token
        state.isAuthenticated = true
        localStorage.setItem('accessToken', action.payload.tokens.access_token)
        localStorage.setItem('refreshToken', action.payload.tokens.refresh_token)
      })
      .addCase(register.rejected, (state, action) => {
        state.loading = false
        state.error =
          getMessageFromApiError(action.payload) ||
          action.error.message ||
          'Registration failed'
      })
  },
})

export const { logout } = authSlice.actions
export default authSlice.reducer
