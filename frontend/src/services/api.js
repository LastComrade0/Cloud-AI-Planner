import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token will be set by the interceptor when auth context is available
let getAuthToken = null

// Function to set the token getter (called from App.jsx)
export const setAuthTokenGetter = (tokenGetter) => {
  getAuthToken = tokenGetter
}

// Add JWT token to requests
api.interceptors.request.use(async (config) => {
  if (getAuthToken) {
    try {
      const token = await getAuthToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch (error) {
      // User not authenticated - request will fail with 401
      console.warn('No auth token available:', error)
    }
  }
  return config
})

export const uploadSyllabus = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/api/v1/upload_syllabus', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const getPlanner = async (fromDate = null, toDate = null) => {
  const params = {}
  if (fromDate) params.from_date = fromDate
  if (toDate) params.to_date = toDate
  
  const response = await api.get('/api/v1/planner', { params })
  return response.data
}

export const updatePlannerItem = async (id, updates) => {
  const response = await api.patch(`/api/v1/planner/${id}`, updates)
  return response.data
}

export const deletePlannerItem = async (id) => {
  await api.delete(`/api/v1/planner/${id}`)
}

export const purgePlanner = async () => {
  await api.delete('/api/v1/planner')
}