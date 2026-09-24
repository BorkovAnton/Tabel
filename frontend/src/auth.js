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
  // Только Администратор: справочник «Коды часов», пользователи и роли
  get isAdmin() {
    return !!this.user && !!this.user.is_admin
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
