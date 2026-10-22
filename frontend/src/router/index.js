import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Employees from '../views/Employees.vue'
import Import from '../views/Import.vue'
import Turnstile from '../views/Turnstile.vue'
import TimesheetReport from '../views/TimesheetReport.vue'
import TurnstileFix from '../views/TurnstileFix.vue'
import Departments from '../views/Departments.vue'
import Schedules from '../views/Schedules.vue'
import Login from '../views/Login.vue'
import Tabels from '../views/Tabels.vue'
import TabelFill from '../views/TabelFill.vue'
import Users from '../views/Users.vue'
import HoursReport from '../views/HoursReport.vue'
import Settings from '../views/Settings.vue'
import Documents from '../views/Documents.vue'
import DismissalNotes from '../views/DismissalNotes.vue'
import { auth } from '../auth'

const routes = [
  // Модуль «Табель»: авторизация обязательна
  { path: '/login', name: 'Login', component: Login },
  { path: '/tabels', name: 'Tabels', component: Tabels, meta: { requiresAuth: true } },
  { path: '/tabels/:id', name: 'TabelFill', component: TabelFill, meta: { requiresAuth: true } },
  { path: '/tabels/:id/print', name: 'TabelPrint', component: () => import('../views/TabelPrint.vue'), meta: { requiresAuth: true } },
  // Увольнительные записки — авторизация обязательна
  { path: '/dismissal-notes', name: 'DismissalNotes', component: DismissalNotes, meta: { requiresAuth: true } },
  { path: '/users', name: 'Users', component: Users, meta: { requiresAuth: true, requiresAdmin: true } },
  // Документы и приказы — авторизация + роль «Документы и приказы» (см. beforeEach)
  { path: '/documents', name: 'Documents', component: Documents, meta: { requiresAuth: true, requiresDocuments: true } },
  // Сводный отчёт часов — роль «Отчёт» (а также администратор/кадровик)
  { path: '/hours-report', name: 'HoursReport', component: HoursReport, meta: { requiresAuth: true, requiresReport: true } },

  { path: '/', name: 'Home', component: Home },
  { path: '/employees', name: 'Employees', component: Employees },
  // Импорт и расчёт табеля — служебные операции, только Администратор
  { path: '/import', name: 'Import', component: Import, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/turnstile', name: 'Turnstile', component: Turnstile },
  { path: '/timesheet-report', name: 'TimesheetReport', component: TimesheetReport },
  { path: '/turnstile-fix', name: 'TurnstileFix', component: TurnstileFix },
  { path: '/departments', name: 'Departments', component: Departments },
  { path: '/schedules', name: 'Schedules', component: Schedules },
  // Настройки предприятия — только Администратор
  { path: '/settings', name: 'Settings', component: Settings, meta: { requiresAuth: true, requiresAdmin: true } }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

// Табель открывается только по числовому id (/tabels/12).
// Если в адресе не число (например /tabels/undefined из-за кэша старого бандла) —
// перенаправляем на список табелей, иначе запрос к API вернёт 422.
router.beforeEach((to) => {
  if (to.name === 'TabelFill') {
    const raw = Array.isArray(to.params.id) ? to.params.id[0] : to.params.id
    if (!/^\d+$/.test(String(raw))) {
      return { name: 'Tabels' }
    }
  }
})

// Пуская на сайт — сразу на окно авторизации модуля Табель
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  // Уже авторизованному не нужно окно входа — отправляем его туда, откуда он пришёл
  // (или на страницу из ?redirect=), либо на список табелей.
  if (to.name === 'Login' && token) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : null
    if (redirect && redirect !== '/login' && !redirect.startsWith('/login?')) {
      return redirect
    }
    return { name: 'Tabels' }
  }
  if (to.meta.requiresAuth && !token) {
    // Редирект на логин с сохранением целевого пути для возврата после входа
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin) {
    let user = null
    try { user = JSON.parse(localStorage.getItem('user') || 'null') } catch (e) { /* noop */ }
    if (!user || !user.is_admin) {
      return { name: 'Tabels' }
    }
  }
  if (to.meta.requiresDocuments) {
    let user = null
    try { user = JSON.parse(localStorage.getItem('user') || 'null') } catch (e) { /* noop */ }
    const ok = !!user && (user.is_documents_manager || user.is_admin || user.is_hr)
    if (!ok) {
      return { name: 'Tabels' }
    }
  }
  if (to.meta.requiresReport) {
    let user = null
    try { user = JSON.parse(localStorage.getItem('user') || 'null') } catch (e) { /* noop */ }
    if (!user || !(user.is_report || user.is_admin || user.is_hr)) {
      return { name: 'Tabels' }
    }
  }
  // ✅ Система управления доступом к вкладкам: если у пользователя заданы permissions
  // и текущая страница в них отсутствует — редирект на первую доступную страницу.
  // (Администраторы и пользователи без permissions имеют доступ ко всем вкладкам.)
  if (auth.isAuthenticated && auth.user && Array.isArray(auth.user.permissions) && auth.user.permissions.length > 0 && !auth.user.is_admin) {
    const pagePath = to.path === '/tabels' || to.path.startsWith('/tabels/') ? '/tabels' : to.path
    const isPublicPage = to.name === 'Login' || to.name === 'Home'
    if (!isPublicPage && !auth.hasPermission(pagePath)) {
      const firstAvailable = auth.user.permissions.find(p => p !== '/') || '/tabels'
      if (firstAvailable === to.path) return true
      return firstAvailable
    }
  }
  if (to.name === 'Home' && !token) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
