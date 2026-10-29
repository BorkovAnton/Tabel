import { reactive } from 'vue'
import api from './api'

export const auth = reactive({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token'),

  get isAuthenticated() {
    return !!this.token
  },
  // ✅ ЭТАП 8: фронтенд работает ТОЛЬКО с новой системой прав:
  // role ('admin','hr','manager','inspector','accountant','user'),
  // data_scope ('own','department','custom','all'), can_* флаги и permissions (пути вкладок).
  // Старые булевы поля (is_admin, is_hr, timesheet_inspector, is_user, is_report,
  // is_documents_manager) на фронтенде БОЛЬШЕ НЕ используются — они остались
  // только в моделях бэкенда/БД как тихий фолбэк.

  // Только Администратор: справочник «Коды часов», пользователи и роли.
  get isAdmin() {
    return !!this.user && this.user.role === 'admin'
  },

  // Кадровик (администратор обладает правами кадровика).
  get isHR() {
    return !!this.user && (this.user.role === 'hr' || this.user.role === 'admin')
  },

  // Инспектор табелей: видит все табели (adm/hr — по умолчанию тоже).
  get isTimesheetInspector() {
    return !!this.user && (
      this.user.role === 'inspector' ||
      this.user.role === 'admin' ||
      this.user.role === 'hr' ||
      // спец-флаги новой системы
      !!this.user.can_view_all_tabels
    )
  },

  // Базовый доступ: любая назначенная роль.
  get isUser() {
    return !!this.user && !!this.user.role
  },

  // Создание/удаление табелей: admin / hr / manager либо спец-право can_approve.
  get canManageTabels() {
    return !!this.user && (
      this.user.role === 'admin' ||
      this.user.role === 'hr' ||
      this.user.role === 'manager' ||
      !!this.user.can_approve
    )
  },

  // Роль «Отчёт»: страница сводного отчёта часов (табель vs факт).
  get isReport() {
    return !!this.user && (
      this.user.role === 'admin' ||
      this.user.role === 'hr' ||
      this.user.role === 'accountant'
    )
  },

  // Роль «Документы и приказы»: ввод событий сотрудников (отпуска, командировки, больничные).
  get isDocumentsManager() {
    return !!this.user && (
      this.user.role === 'admin' ||
      this.user.role === 'hr'
    )
  },

  // Область видимости данных (new system): 'own' | 'department' | 'custom' | 'all'.
  get dataScope() {
    return this.user?.data_scope || 'own'
  },

  // ✅ Права доступа к вкладкам сайта (только новая система).
  // Ключ вкладки = путь страницы ('/', '/tabels', '/employees', ...).
  // Правила:
  //  - администратор (role === 'admin') имеет доступ ко всем вкладкам;
  //  - если permissions не заданы (null/пусто), но есть роль — базовый доступ к табелям;
  //  - иначе — только вкладки из списка permissions ('/' даёт доступ ко всем вкладкам).
  hasPermission(path) {
    if (!this.user) return false
    if (this.user.role === 'admin') return true
    const perms = this.user.permissions
    if (!Array.isArray(perms) || perms.length === 0) {
      // Если permissions пуст, но есть роль, даём базовый доступ к табелям
      return path === '/tabels' || path === '/' || path === ''
    }
    return perms.includes(path) || perms.includes('/')
  },

  // Обновить данные пользователя с сервера (например, после смены прав)
  async refresh() {
    if (!this.token) return null
    try {
      const { data } = await api.get('/auth/me')
      this.user = data
      localStorage.setItem('user', JSON.stringify(data))
      return data
    } catch (e) {
      return null
    }
  },

  async login(username, password) {
    try {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const { data } = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      return data.user
    } catch (error) {
      console.error('Ошибка входа:', error)
      // Пробрасываем ошибку, чтобы компонент Login мог её обработать и остановить спиннер
      throw error
    }
  },

  // ✅ Первая доступная пользователю страница (для умного редиректа после входа).
  // ЭТАП 8: опирается только на новую систему (role / permissions).
  firstAvailablePage() {
    if (!this.user) return null
    // Администратор по роли — доступ ко всем вкладкам
    if (this.user.role === 'admin') return '/tabels'
    const perms = this.user.permissions
    if (!Array.isArray(perms) || perms.length === 0) {
      // Пустые permissions — базовая страница по умолчанию (совпадает с hasPermission)
      return '/tabels'
    }
    // Первая реально доступная страница ('/' даёт доступ ко всем вкладкам)
    if (perms.includes('/')) return '/tabels'
    return perms.find(p => typeof p === 'string' && p !== '/login') || '/tabels'
  },

  logout() {
    this.token = null
    this.user = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }
})

// Синхронизация reactive-состояния при внешней очистке сессии (глобальный перехватчик 401 в api.js)
window.addEventListener('auth:session-expired', () => {
  auth.token = null
  auth.user = null
})
