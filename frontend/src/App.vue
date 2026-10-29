<template>
  <v-app>
    <v-app-bar color="#2d5a3d" elevation="2">
      <v-toolbar-title style="color: white; font-weight: bold;">
        TabelSystem
      </v-toolbar-title>

      <v-spacer></v-spacer>

      <template v-if="auth.isAuthenticated">
        <!-- Компактный список: если пунктов много, остальные в меню «Ещё» -->
        <v-btn
          v-for="item in visibleNavItems"
          :key="item.path"
          :to="item.path"
          variant="text"
          style="color: rgba(255,255,255,0.9);"
        >
          <v-icon start size="small">{{ item.icon }}</v-icon>
          {{ item.title }}
        </v-btn>

        <v-menu v-if="hiddenNavItems.length" offset-y>
          <template #activator="{ props }">
            <v-btn v-bind="props" variant="text" style="color: rgba(255,255,255,0.9);">
              <v-icon start size="small">mdi-dots-horizontal</v-icon>
              Ещё
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item
              v-for="item in hiddenNavItems"
              :key="item.path"
              :prepend-icon="item.icon"
              :title="item.title"
              :to="item.path"
            />
          </v-list>
        </v-menu>

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

// ✅ ЭТАП 9.5: меню строится ИСКЛЮЧИТЕЛЬНО на основе auth.hasPermission(path).
// Единственные дополнительные условия — авторизация (auth: true) и спец-право
// can_manage_users для пункта «Пользователи» (новая система can_* флагов).
const allNavItems = [
  { title: 'Сводка', path: '/', icon: 'mdi-view-dashboard' },
  { title: 'Сотрудники', path: '/employees', icon: 'mdi-account-group' },
  { title: 'Импорт', path: '/import', icon: 'mdi-file-import', auth: true },
  { title: 'Расчёт событий', path: '/turnstile-fix', icon: 'mdi-calculator' },
  { title: 'Табель фактический', path: '/timesheet-report', icon: 'mdi-calendar-month' },
  { title: 'Отчёт по часам', path: '/hours-report', icon: 'mdi-chart-box', auth: true },
  { title: 'Подразделения', path: '/departments', icon: 'mdi-office-building' },
  { title: 'Графики', path: '/schedules', icon: 'mdi-clock-outline' },
  { title: 'Настройки', path: '/settings', icon: 'mdi-cog', auth: true },
  { title: 'Табель', path: '/tabels', icon: 'mdi-table-large', auth: true },
  { title: 'Увольнительные записки', path: '/dismissal-notes', icon: 'mdi-clock-alert-outline', auth: true },
  { title: 'Документы', path: '/documents', icon: 'mdi-file-document-edit-outline', auth: true },
  { title: 'Пользователи', path: '/users', icon: 'mdi-account-key', manageUsers: true }
]

const navItems = computed(() => allNavItems.filter(i => {
  // Пункты, требующие входа в систему
  if (i.auth && !auth.isAuthenticated) return false
  // Спец-право новой системы: управление пользователями
  if (i.manageUsers && !(auth.isAdmin || !!auth.user?.can_manage_users)) return false
  // ✅ Главное условие: вкладка видна, только если есть право доступа к её пути
  // (hasPermission: role === 'admin' — всё; иначе список permissions, '/' = все вкладки)
  return auth.hasPermission(i.path)
}))

// На узких экранах часть пунктов уходит в меню «Ещё», чтобы ничего не пропало
const MAX_VISIBLE = 6
const visibleNavItems = computed(() => navItems.value.slice(0, MAX_VISIBLE))
const hiddenNavItems = computed(() => navItems.value.slice(MAX_VISIBLE))

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
