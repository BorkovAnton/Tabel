import { reactive } from 'vue'
import api from './api'

export const auth = reactive({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token'),

  get isAuthenticated() {
    return !!this.token
  },
  // ✅ ЭТАП 7: геттеры проверяют И старые булевы поля, И новые поля role/permissions
  // (полная обратная совместимость со старыми пользователями).

  // Инспектор табелей: Администратор или Кадровик с ролью «Инспектор табелей» — видит все табели.
  // Старое поле ИЛИ новая роль 'inspector'
  get isTimesheetInspector() {
    return !!this.user && (
      ((this.user.is_admin || this.user.is_hr) && this.user.timesheet_inspector) ||
      this.user.role === 'inspector'
    )
  },
  // Роль «Пользователь»: базовая роль — меню «Табель», «Табель фактический»,
  // создание и заполнение табелей (где он ответственный).
  // Старое поле ИЛИ наличие любой новой роли ИЛИ непустой список permissions
  get isUser() {
    return !!this.user && (
      !!this.user.is_user ||
      !!this.user.role ||
      (Array.isArray(this.user.permissions) && this.user.permissions.length > 0)
    )
  },
  // Создание/удаление табелей: пользователь либо инспектор табелей (или спец-право can_approve)
  get canManageTabels() {
    return this.isUser || this.isTimesheetInspector || !!this.user?.can_approve
  },
  // Кадровик: старое поле ИЛИ новая роль 'hr'
  get isHR() {
    return !!this.user && (!!this.user.is_hr || this.user.role === 'hr')
  },
  // Роль «Отчёт»: страница сводного отчёта часов (табель vs факт).
  // Старое поле ИЛИ роль accountant/hr/admin
  get isReport() {
    return !!this.user && (
      !!this.user.is_report ||
      !!this.user.is_admin || !!this.user.is_hr ||
      this.user.role === 'admin' ||
      this.user.role === 'hr' ||
      this.user.role === 'accountant'
    )
  },
  // Роль «Документы и приказы»: ввод событий сотрудников (отпуска, командировки, больничные).
  // Старое поле ИЛИ роль hr/admin
  get isDocumentsManager() {
    return !!this.user && (
      !!this.user.is_documents_manager ||
      !!this.user.is_admin || !!this.user.is_hr ||
      this.user.role === 'admin' ||
      this.user.role === 'hr'
    )
  },
  // Только Администратор: справочник «Коды часов», пользователи и роли.
  // Старое поле ИЛИ новая роль 'admin'
  get isAdmin() {
    return !!this.user && (!!this.user.is_admin || this.user.role === 'admin')
  },

  // ✅ Права доступа к вкладкам сайта.
  // Ключ вкладки = путь страницы ('/', '/tabels', '/employees', ...).
  // Правила:
  //  - администратор имеет доступ ко всем вкладкам;
  //  - если permissions не заданы (null/пусто) — доступны все вкладки
  //    (обратная совместимость со старыми пользователями);
  //  - иначе — только вкладки из списка permissions.
  hasPermission(path) {
    if (!this.user) return false
    // Администратор: старое поле ИЛИ новая роль — доступ ко всем вкладкам
    if (this.user.is_admin || this.user.role === 'admin') return true
    const perms = this.user.permissions
    if (!Array.isArray(perms) || perms.length === 0) {
      // Если permissions пустые, но есть базовая роль, даём доступ к табелям по умолчанию
      if (this.user.role) return path === '/tabels' || path === '/'
      return true // Обратная совместимость со старыми пользователями без ролей
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
  // Правила совпадают с hasPermission: админ — любая, пустые permissions — '/tabels'.
  firstAvailablePage() {
    if (!this.user) return null
    // Администратор: старое поле ИЛИ новая роль — доступ ко всем вкладкам
    if (this.user.is_admin || this.user.role === 'admin') return '/tabels'
    const perms = this.user.permissions
    if (!Array.isArray(perms) || perms.length === 0) {
      // Пустые permissions + новая роль — по умолчанию табели (совпадает с hasPermission)
      if (this.user.role) return '/tabels'
      return '/tabels' // Обратная совместимость: старые пользователи видят все вкладки
    }
    // Первая реально доступная страница ('/' даёт доступ ко всем вкладкам)
    if (perms.includes('/')) return '/tabels'
    return perms[0] || '/tabels'
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
