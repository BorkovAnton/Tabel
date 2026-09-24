<template>
  <v-app>
    <v-app-bar color="#2d5a3d" elevation="2">
      <v-toolbar-title style="color: white; font-weight: bold;">
        TabelSystem
      </v-toolbar-title>
      
      <v-spacer></v-spacer>
      
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
    </v-app-bar>

    <v-main style="background-color: #f1f8e9;">
      <v-container fluid class="pa-6">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref } from 'vue'

const navItems = ref([
  { title: 'Сводка', path: '/', icon: 'mdi-view-dashboard' },
  { title: 'Сотрудники', path: '/employees', icon: 'mdi-account-group' },
  { title: 'Импорт', path: '/import', icon: 'mdi-file-import' },
  { title: 'Расчёт событий', path: '/turnstile-fix', icon: 'mdi-calculator' },
  { title: 'Табель фактический', path: '/timesheet-report', icon: 'mdi-calendar-month' },
  { title: 'Подразделения', path: '/departments', icon: 'mdi-office-building' },
  { title: 'Графики', path: '/schedules', icon: 'mdi-clock-outline' }
])
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