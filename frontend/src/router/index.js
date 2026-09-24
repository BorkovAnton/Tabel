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

const routes = [
  // Модуль «Табель»: авторизация обязательна
  { path: '/login', name: 'Login', component: Login },
  { path: '/tabels', name: 'Tabels', component: Tabels, meta: { requiresAuth: true } },
  { path: '/tabels/:id', name: 'TabelFill', component: TabelFill, meta: { requiresAuth: true } },

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

// Пуская на сайт — сразу на окно авторизации модуля Табель
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { name: 'Login' }
  }
  if (to.name === 'Home' && !token) {
    return { name: 'Login' }
  }
  return true
})

export default router
