import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Employees from '../views/Employees.vue'
import Import from '../views/Import.vue'
import Turnstile from '../views/Turnstile.vue'
import TimesheetReport from '../views/TimesheetReport.vue'
import TurnstileFix from '../views/TurnstileFix.vue'
import Departments from '../views/Departments.vue'
import Schedules from '../views/Schedules.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/employees',
    name: 'Employees',
    component: Employees
  },
  {
    path: '/import',
    name: 'Import',
    component: Import
  },
  {
    path: '/turnstile',
    name: 'Turnstile',
    component: Turnstile
  },
  {
    path: '/timesheet-report',
    name: 'TimesheetReport',
    component: TimesheetReport
  },
  { 
    path: '/turnstile-fix', 
    name: 'TurnstileFix', 
    component: TurnstileFix 
  },
    { 
    path: '/departments', 
    name: 'Departments', 
    component: Departments 
  },
  { path: '/schedules',
     name: 'Schedules',
      component: Schedules 
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router