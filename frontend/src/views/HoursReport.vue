<template>
  <div>
    <h2 class="mb-4">Отчёт по часам</h2>

    <v-card class="pa-4 mb-4">
      <v-row align="center">
        <v-col cols="12" md="3">
          <v-select
            v-model="month"
            :items="months"
            item-title="title"
            item-value="value"
            label="Месяц"
            variant="outlined"
            density="comfortable"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="year"
            :items="years"
            label="Год"
            variant="outlined"
            density="comfortable"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-btn color="primary" :loading="loading" @click="loadReport">
            <v-icon start size="small">mdi-magnify</v-icon>
            Сформировать
          </v-btn>
        </v-col>
      </v-row>
    </v-card>

    <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>

    <v-card class="pa-4">
      <v-data-table
        :headers="headers"
        :items="rows"
        :loading="loading"
        items-per-page-text="Строк на странице:"
        class="hours-report-table"
      >
        <template #item.tabel_hours="{ item }">
          {{ fmt(item.tabel_hours) }}
        </template>
        <template #item.fact_hours="{ item }">
          {{ fmt(item.fact_hours) }}
        </template>
        <template #item.overtime_hours="{ item }">
          <span :class="{ 'text-red': item.overtime_hours > 0, 'font-weight-bold': item.overtime_hours > 0 }">
            {{ fmt(item.overtime_hours) }}
          </span>
        </template>
        <template #footer>
          <tr>
            <td colspan="4" class="text-right font-weight-bold">Итого:</td>
            <td class="font-weight-bold text-right">{{ fmt(sumTabel) }}</td>
            <td class="font-weight-bold text-right">{{ fmt(sumFact) }}</td>
            <td class="font-weight-bold text-right">{{ fmt(sumOvertime) }}</td>
          </tr>
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import api from '../api'

const MONTH_TITLES = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

const now = new Date()
const month = ref(now.getMonth() + 1)
const year = ref(now.getFullYear())
const months = MONTH_TITLES.map((title, i) => ({ title, value: i + 1 }))
const years = Array.from({ length: 6 }, (_, i) => now.getFullYear() - 3 + i)

const rows = ref([])
const loading = ref(false)
const error = ref('')

const headers = [
  { title: 'ФИО', key: 'full_name', sortable: true },
  { title: 'Табельный', key: 'tab_number', sortable: false },
  { title: 'Подразделение', key: 'department_name', sortable: false },
  { title: 'Часы с табеля', key: 'tabel_hours', sortable: true, align: 'end' },
  { title: 'Часы фактические', key: 'fact_hours', sortable: true, align: 'end' },
  { title: 'Сверхурочно', key: 'overtime_hours', sortable: true, align: 'end' },
]

const sumTabel = computed(() => rows.value.reduce((s, r) => s + (r.tabel_hours || 0), 0))
const sumFact = computed(() => rows.value.reduce((s, r) => s + (r.fact_hours || 0), 0))
const sumOvertime = computed(() => rows.value.reduce((s, r) => s + (r.overtime_hours || 0), 0))

function fmt(v) {
  const n = Number(v) || 0
  // форматируем как «168ч15м»
  const hh = Math.floor(n)
  const mm = Math.round((n - hh) * 60)
  if (mm === 60) return `${hh + 1}ч`
  return mm ? `${hh}ч${mm}м` : `${hh}ч`
}

async function loadReport() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/reports/hours', { params: { year: year.value, month: month.value } })
    rows.value = data.rows || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка загрузки отчёта'
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadReport)
</script>

<style scoped>
.hours-report-table :deep(th) {
  white-space: nowrap;
}
</style>
