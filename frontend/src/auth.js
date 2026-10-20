import { reactive } from 'vue'
import api from './api'

export const auth = reactive({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token'),

  get isAuthenticated() {
    return !!this.token
  },
  // Инспектор табелей: Администратор или Кадровик с ролью «Инспектор табелей» — видит все табели
  get isTimesheetInspector() {
    return !!this.user && (this.user.is_admin || this.user.is_hr) && this.user.timesheet_inspector
  },
  // Роль «Пользователь»: базовая роль — меню «Табель», «Табель фактический»,
  // создание и заполнение табелей (где он ответственный)
  get isUser() {
    return !!this.user && !!this.user.is_user
  },
  // Создание/удаление табелей: пользователь либо инспектор табелей
  get canManageTabels() {
    return this.isUser || this.isTimesheetInspector
  },
  // Кадровик (без роли инспектора табелей)
  get isHR() {
    return !!this.user && !!this.user.is_hr
  },
  // Роль «Отчёт»: страница сводного отчёта часов (табель vs факт)
  get isReport() {
    return !!this.user && (!!this.user.is_report || !!this.user.is_admin || !!this.user.is_hr)
  },
  // Роль «Документы и приказы»: ввод событий сотрудников (отпуска, командировки, больничные)
  get isDocumentsManager() {
    return !!this.user && (!!this.user.is_documents_manager || !!this.user.is_admin || !!this.user.is_hr)
  },
  // Только Администратор: справочник «Коды часов», пользователи и роли
  get isAdmin() {
    return !!this.user && !!this.user.is_admin
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
    if (this.user.is_admin) return true
    const perms = this.user.permissions
    if (!Array.isArray(perms) || perms.length === 0) return true
    return perms.includes(path)
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
