<template>
  <v-app>
    <v-app-bar color="#2d5a3d" elevation="2">
      <v-toolbar-title style="color: white; font-weight: bold;">
        TabelSystem
      </v-toolbar-title>

      <v-spacer></v-spacer>

      <template v-if="auth.isAuthenticated">
        <v-btn
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          variant="text"
          style="color: rgba(255,255,255,0.9);"
        >
          <v-icon start size="small">{{ item.icon }}</v-icon>
          {{ item.title }}
        </v-btn>

        <v-menu offset-y>
          <template #activator="{ props }">
            <v-btn v-bind="props" variant="text" style="color: rgba(255,255,255,0.9);">
              <v-icon start size="small">mdi-account-circle</v-icon>
              {{ auth.user?.full_name || auth.user?.username }}
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item v-if="auth.isTimesheetInspector" prepend-icon="mdi-shield-check" title="Инспектор табелей" />
            <v-list-item prepend-icon="mdi-logout" title="Выйти" @click="logout" />
          </v-list>
        </v-menu>
      </template>
    </v-app-bar>

    <v-main style="background-color: #f1f8e9;">
      <v-container fluid class="pa-6">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from './auth'

const router = useRouter()

const allNavItems = [
  { title: 'Сводка', path: '/', icon: 'mdi-view-dashboard', auth: false },
  { title: 'Сотрудники', path: '/employees', icon: 'mdi-account-group', auth: false },
  { title: 'Импорт', path: '/import', icon: 'mdi-file-import', auth: false },
  { title: 'Расчёт событий', path: '/turnstile-fix', icon: 'mdi-calculator', auth: false },
  { title: 'Табель фактический', path: '/timesheet-report', icon: 'mdi-calendar-month', auth: false },
  { title: 'Подразделения', path: '/departments', icon: 'mdi-office-building', auth: false },
  { title: 'Графики', path: '/schedules', icon: 'mdi-clock-outline', auth: false },
  { title: 'Табель', path: '/tabels', icon: 'mdi-table-large', auth: true },
  { title: 'Пользователи', path: '/users', icon: 'mdi-account-key', admin: true }
]

const navItems = computed(() => allNavItems.filter(i => {
  if (i.auth && !auth.isAuthenticated) return false
  if (i.admin && !auth.isAdmin) return false
  return true
}))

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
/* Минимальные стили */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.v-application__wrap {
  background-color: #f1f8e9 !important;
}

h1, h2, h3, h4, h5, h6 {
  color: #2d5a3d !important;
}

.v-btn--variant-elevated,
.v-btn--variant-flat,
.v-btn--color-primary {
  background-color: #2d5a3d !important;
  color: white !important;
}

.v-data-table thead th {
  background-color: #2d5a3d !important;
  color: white !important;
}

.v-chip {
  background-color: #4a7c59 !important;
  color: white !important;
}
</style>
