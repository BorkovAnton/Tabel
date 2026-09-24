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

const routes = [
  // Модуль «Табель»: авторизация обязательна
  { path: '/login', name: 'Login', component: Login },
  { path: '/tabels', name: 'Tabels', component: Tabels, meta: { requiresAuth: true } },
  { path: '/tabels/:id', name: 'TabelFill', component: TabelFill, meta: { requiresAuth: true } },
  { path: '/users', name: 'Users', component: Users, meta: { requiresAuth: true, requiresAdmin: true } },

  { path: '/', name: 'Home', component: Home },
  { path: '/employees', name: 'Employees', component: Employees },
  { path: '/import', name: 'Import', component: Import },
  { path: '/turnstile', name: 'Turnstile', component: Turnstile },
  { path: '/timesheet-report', name: 'TimesheetReport', component: TimesheetReport },
  { path: '/turnstile-fix', name: 'TurnstileFix', component: TurnstileFix },
  { path: '/departments', name: 'Departments', component: Departments },
  { path: '/schedules', name: 'Schedules', component: Schedules }
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
  if (to.meta.requiresAuth && !token) {
    return { name: 'Login' }
  }
  if (to.meta.requiresAdmin) {
    let user = null
    try { user = JSON.parse(localStorage.getItem('user') || 'null') } catch (e) { /* noop */ }
    if (!user || !user.is_admin) {
      return { name: 'Tabels' }
    }
  }
  if (to.name === 'Home' && !token) {
    return { name: 'Login' }
  }
  return true
})

export default router
