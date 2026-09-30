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
        <v-col cols="12" md="2">
          <v-autocomplete
            v-model="selectedDepartment"
            :items="sortedDepartments"
            item-title="title"
            item-value="id"
            label="Подразделение"
            variant="outlined"
            density="comfortable"
            clearable
            prepend-inner-icon="mdi-office-building"
            placeholder="Начните вводить название…"
            no-data-text="Подразделение не найдено"
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
          <!-- розовый, если фактические часы меньше часов с табеля -->
          <span :class="{ 'pink-highlight': num(item.fact_hours) < num(item.tabel_hours) }">
            {{ fmt(item.fact_hours) }}
          </span>
        </template>
        <template #item.overtime_planned="{ item }">
          {{ fmt(item.overtime_planned) }}
        </template>
        <template #item.overtime_hours="{ item }">
          <!-- розовый, если сверхурочно факт меньше сверхурочного с табеля -->
          <span
            :class="{
              'text-red': item.overtime_hours > 0,
              'font-weight-bold': item.overtime_hours > 0,
              'pink-highlight': num(item.overtime_hours) < num(item.overtime_planned),
            }"
          >
            {{ fmt(item.overtime_hours) }}
          </span>
        </template>
        <template #footer>
          <tr>
            <td colspan="4" class="text-right font-weight-bold">Итого:</td>
            <td class="font-weight-bold text-right">{{ fmt(sumTabel) }}</td>
            <td class="font-weight-bold text-right">{{ fmt(sumFact) }}</td>
            <td class="font-weight-bold text-right">{{ fmt(sumOvertimePlanned) }}</td>
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

// Подразделения: сортировка по алфавиту (регистронезависимо).
// В title кладём имя — v-autocomplete фильтрует по подстроке регистронезависимо.
const departments = ref([])
const selectedDepartment = ref(null)
const sortedDepartments = computed(() => {
  return [...departments.value]
    .sort((a, b) => (a.name || '').localeCompare(b.name || '', 'ru', { sensitivity: 'base' }))
    .map(d => ({ ...d, title: d.name }))
})

async function loadDepartments() {
  try {
    const { data } = await api.get('/departments/', { params: { flat: true } })
    departments.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('Ошибка загрузки подразделений:', e)
    departments.value = []
  }
}

const rows = ref([])
const loading = ref(false)
const error = ref('')

const headers = [
  { title: 'ФИО', key: 'full_name', sortable: true },
  { title: 'Табельный', key: 'tab_number', sortable: false },
  { title: 'Подразделение', key: 'department_name', sortable: false },
  { title: 'Часы с табеля', key: 'tabel_hours', sortable: true, align: 'end' },
  { title: 'Часы фактические', key: 'fact_hours', sortable: true, align: 'end' },
  { title: 'Сверхурочно с табеля', key: 'overtime_planned', sortable: true, align: 'end' },
  { title: 'Сверхурочно факт', key: 'overtime_hours', sortable: true, align: 'end' },
]

const sumTabel = computed(() => rows.value.reduce((s, r) => s + (r.tabel_hours || 0), 0))
const sumFact = computed(() => rows.value.reduce((s, r) => s + (r.fact_hours || 0), 0))
const sumOvertimePlanned = computed(() => rows.value.reduce((s, r) => s + (r.overtime_planned || 0), 0))
const sumOvertime = computed(() => rows.value.reduce((s, r) => s + (r.overtime_hours || 0), 0))

function num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

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
    const params = { year: year.value, month: month.value }
    // При выбранном подразделении — отчёт формируется только для него
    if (selectedDepartment.value != null && selectedDepartment.value !== '') {
      params.department_id = selectedDepartment.value
    }
    const { data } = await api.get('/reports/hours', { params })
    rows.value = data.rows || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка загрузки отчёта'
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDepartments()
  loadReport()
})
</script>

<style scoped>
.hours-report-table :deep(th) {
  white-space: nowrap;
}

/* Розовая подсветка расхождений (факт меньше план/табеля) */
.pink-highlight {
  background-color: #f8bbd0;
  color: #880e4f;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
</style>
