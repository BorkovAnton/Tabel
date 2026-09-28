import axios from 'axios'

const api = axios.create({
  baseURL: 'http://192.168.100.61:8000',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Прикрепляем JWT-токен ко всем запросам (если пользователь авторизован)
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
