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
      <!-- ИЗМЕНЕНО: пагинация убрана — выводятся все сотрудники сразу
           (:items-per-page="-1" + hide-default-footer). Для длинного списка
           добавлена вертикальная прокрутка с фиксированной шапкой
           (height="70vh" + fixed-header). -->
      <v-data-table
        :headers="headers"
        :items="rows"
        :loading="loading"
        :items-per-page="-1"
        hide-default-footer
        height="70vh"
        fixed-header
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
        <template #item.overtime_total="{ item }">
          <!-- ИЗМЕНЕНО: колонка «Сверхурочно с табеля итого» — только итог
               (сверхурочные часы + сверхурочные дни × норма дня). Разбивка
               «часы без дней» из заголовка и скобок убрана. -->
          <span class="font-weight-bold">{{ fmt(item.overtime_total) }}</span>
        </template>
        <template #item.overtime_hours="{ item }">
          <!-- розовый, если сверхурочно факт меньше сверхурочного с табеля (итого) -->
          <span
            :class="{
              'text-red': item.overtime_hours > 0,
              'font-weight-bold': item.overtime_hours > 0,
              'pink-highlight': num(item.overtime_hours) < num(item.overtime_total),
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
            <td class="font-weight-bold text-right">{{ fmt(sumOvertimeTotal) }}</td>
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
  { title: 'Сверхурочно с табеля итого', key: 'overtime_total', sortable: true, align: 'end' },
  { title: 'Сверхурочно факт', key: 'overtime_hours', sortable: true, align: 'end' },
]

const sumTabel = computed(() => rows.value.reduce((s, r) => s + (r.tabel_hours || 0), 0))
const sumFact = computed(() => rows.value.reduce((s, r) => s + (r.fact_hours || 0), 0))
// ИЗМЕНЕНО: «Сверхурочно с табеля итого» — только итог (часы + дни × норма),
// суммируется поле overtime_total из API; разбивка «часы без дней» убрана.
const sumOvertimeTotal = computed(() => rows.value.reduce((s, r) => s + (r.overtime_total || 0), 0))
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

/* Sticky-шапка при вертикальной прокрутке (height="70vh" + fixed-header).
   ИСПРАВЛЕНО: в Vuetify 3 класс thead th не существует — шапка это
   th.v-data-table-th, поэтому прошлое правило не применялось и оставался
   розовый hover-фон (буква «Н» в :hover → rgba(pink,.04)) поверх светлого
   текста — ничего не было видно. Теперь стиль приведён к общему виду с
   таблицей «Табель фактического»: светло-серый непрозрачный фон, тёмный
   текст, жирные заголовки, тень-разделитель под шапкой. */
.hours-report-table :deep(.v-data-table-header th),
.hours-report-table :deep(th.v-data-table-th) {
  position: sticky;
  top: 0;
  z-index: 5;
  background-color: #eeeeee !important; /* как в табеле: bg-grey-lighten-4, непрозрачный */
  color: rgba(0, 0, 0, 0.87) !important;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25); /* тень-разделитель под липкой шапкой */
}

/* Розовый hover-фон не должен подсвечивать шапку (только строки tbody) */
.hours-report-table :deep(th.v-data-table-th:hover) {
  background-color: #eeeeee !important;
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
