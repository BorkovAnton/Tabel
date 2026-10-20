import axios from 'axios'
// Импортируем роутер через ленивый require() внутри перехватчика, чтобы избежать
// циклической зависимости (router -> views -> auth -> api). См. handleUnauthorized.

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

// === ГЛОБАЛЬНАЯ ОБРАБОТКА ИСТЕЧЕНИЯ СЕССИИ (401 Unauthorized) ===
// При любой 401 ошибке: полностью очищаем состояние авторизации и мягко
// перенаправляем пользователя на /login, сохраняя страницу, куда он шёл (?redirect=...).
let sessionExpiredRedirecting = false // защита от «шума» — несколько 401 подряд дают один редирект

export function handleUnauthorized() {
  // 1. Полностью очищаем данные сессии (токен + пользователь)
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  try {
    // Ленивый импорт auth (модуль авторизации) — безопасно при циклических зависимостях
    const { auth } = require('./auth')
    if (auth && typeof auth.logout === 'function') {
      auth.logout() // очистит reactive-состояние (token/user) и localStorage
    }
  } catch (e) { /* noop */ }
  // Синхронизируем reactive-состояние auth, модуль которого уже загружен в другом месте
  window.dispatchEvent(new Event('auth:session-expired'))

  // 2. Редирект на страницу входа с сохранением текущего пути для возврата
  if (sessionExpiredRedirecting) return
  try {
    const router = require('./router').default
    const currentPath = router.currentRoute.value.fullPath
    if (router.currentRoute.value.name !== 'Login') {
      sessionExpiredRedirecting = true
      router.push({ path: '/login', query: { redirect: currentPath } }).finally(() => {
        sessionExpiredRedirecting = false
      })
    }
  } catch (e) {
    // Роутер ещё не готов — fallback на жёсткую перезагрузку страницы логина
    sessionExpiredRedirecting = false
    window.location.assign('/login?redirect=' + encodeURIComponent(window.location.pathname + window.location.search))
  }
}

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // 401 на самом входе (/auth/login) — это неверный логин/пароль, а не истечение сессии:
      // показываем ошибку на странице входа, без редиректа и очистки состояния.
      const url = (error.config && error.config.url) || ''
      if (!url.includes('/auth/login')) {
        console.warn('Сессия истекла или токен недействителен, выполняется выход...')
        handleUnauthorized()
      }
    }
    return Promise.reject(error)
  }
)

export default api
