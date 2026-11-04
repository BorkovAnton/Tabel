<template>
  <div>
    <v-row class="mb-2" align="center">
      <v-col cols="auto">
        <h2 class="text-h5 font-weight-bold">Все проходы</h2>
        <div class="text-caption text-grey-darken-1">
          Сверка фактических проходов с турникета перед расчётом табеля
        </div>
      </v-col>
    </v-row>

    <!-- Фильтры: месяц + сотрудник -->
    <v-card elevation="2" class="mb-4 pa-4" border>
      <v-row dense align="center">
        <v-col cols="12" sm="4" md="3">
          <v-menu v-model="monthMenu" :close-on-content-click="false" transition="scale-transition"
                  min-width="290px">
            <template #activator="{ props }">
              <v-text-field
                :model-value="monthLabel"
                label="Месяц"
                prepend-inner-icon="mdi-calendar-month"
                readonly
                v-bind="props"
                hide-details="auto"
              />
            </template>
            <v-date-picker
              v-model="monthPicker"
              type="month"
              color="#2d5a3d"
              title="Выберите месяц"
              @update:model-value="onMonthChange"
            />
          </v-menu>
          <!-- Стрелки для быстрой смены месяца -->
          <div class="d-flex align-center mt-1 ga-1">
            <v-btn size="x-small" variant="tonal" icon="mdi-chevron-left" @click="shiftMonth(-1)" />
            <v-btn size="x-small" variant="tonal" icon="mdi-chevron-right" @click="shiftMonth(1)" />
            <span class="text-caption text-grey ml-2">{{ monthLabel }}</span>
          </div>
        </v-col>

        <v-col cols="12" sm="8" md="5">
          <v-autocomplete
            v-model="selectedEmployee"
            :items="employeeItems"
            item-title="title"
            item-value="id"
            label="Сотрудник (поиск по ФИО)"
            prepend-inner-icon="mdi-magnify"
            clearable
            :loading="searchLoading"
            return-object
            hide-details="auto"
            density="comfortable"
            no-filter
            @update:search="onSearchInput"
            @update:model-value="loadPasses"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props" :title="item.raw.full_name">
                <template #append>
                  <span class="text-caption text-grey">{{ item.raw.tab_number || '' }}</span>
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>
        </v-col>

        <v-col cols="12" md="4" class="d-flex align-center">
          <v-progress-circular v-if="loading" indeterminate size="20" width="2" color="#2d5a3d" class="mr-3" />
          <div v-if="events.length" class="text-body-2">
            Всего событий: <b>{{ events.length }}</b>
            (входов: <b class="text-success">{{ inCount }}</b>,
            выходов: <b class="text-error">{{ outCount }}</b>
            <template v-if="shiftCount">, смен вручную: <b class="text-info">{{ shiftCount }}</b></template>)
          </div>
        </v-col>
      </v-row>
    </v-card>

    <!-- Подсказка, пока сотрудник не выбран -->
    <v-alert v-if="!selectedEmployee" type="info" variant="toned" icon="mdi-account-search" class="mb-4">
      Выберите сотрудника — таблица покажет все его фактические проходы за выбранный месяц.
    </v-alert>

    <v-alert v-else-if="error" type="error" variant="toned" closable icon="mdi-alert-circle" class="mb-4">
      {{ error }}
    </v-alert>

    <!-- Нет проходов -->
    <v-alert v-else-if="!loading && events.length === 0" type="warning" variant="toned"
             icon="mdi-calendar-remove" class="mb-4">
      Проходов не найдено за {{ monthLabel }}{{ employeeTitle ? ` — ${employeeTitle}` : '' }}.
    </v-alert>

    <!-- Таблица проходов -->
    <v-card v-if="selectedEmployee && events.length" elevation="2" border>
      <v-table hover density="comforted" class="passes-table">
        <thead>
          <tr>
            <th class="text-left" style="width: 60px;">№</th>
            <th class="text-left" style="width: 140px;">Дата</th>
            <th class="text-left" style="width: 140px;">День недели</th>
            <th class="text-left" style="width: 120px;">Время</th>
            <th class="text-left" style="width: 180px;">Тип события</th>
            <th class="text-left">Примечание</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, idx) in tableRows"
            :key="row.event.id"
            :class="{ 'day-alt': row.dayIndex % 2 === 1, 'new-day': row.isFirstOfDay }"
          >
            <td class="text-grey">{{ idx + 1 }}</td>
            <td :class="{ 'font-weight-bold': row.isFirstOfDay }">{{ row.dateStr }}</td>
            <td :class="row.weekend ? 'text-error' : ''">{{ row.weekdayStr }}</td>
            <td class="font-weight-medium">{{ row.timeStr }}</td>
            <td>
              <v-chip v-if="row.event.event_type === 'in'" size="small" variant="flat"
                      :style="{ backgroundColor: '#e6f4ea', color: '#1e7e34' }" prepend-icon="mdi-login">
                Вход
              </v-chip>
              <v-chip v-else-if="row.event.event_type === 'out'" size="small" variant="flat"
                      :style="{ backgroundColor: '#fdecea', color: '#c62828' }" prepend-icon="mdi-logout">
                Выход
              </v-chip>
              <v-chip v-else-if="row.event.event_type === 'shift'" size="small" variant="flat"
                      :style="{ backgroundColor: '#e3f2fd', color: '#1565c0' }" prepend-icon="mdi-bookmark-plus">
                Смена (вручную)
              </v-chip>
              <v-chip v-else size="small" variant="outlined">{{ row.event.event_type }}</v-chip>
            </td>
            <td class="text-caption">
              <span v-if="row.event.is_manual" class="text-orange font-weight-medium">(внесено вручную)</span>
              <span v-if="row.event.shift_end"> — выход {{ fmtTime(row.event.shift_end) }}</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api'

// ---------- Месяц (по умолчанию — текущий) ----------
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1) // 1..12
const monthMenu = ref(false)

// v-date-picker type="month" хранит ISO-строку "YYYY-MM"
const monthPicker = ref(`${year.value}-${String(month.value).padStart(2, '0')}`)

const MONTH_NAMES = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]
const WEEKDAYS = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

const monthLabel = computed(() => `${MONTH_NAMES[month.value - 1]} ${year.value}`)
const monthDisplay = computed(() => monthLabel.value)

function onMonthChange(val) {
  if (!val) return
  const d = new Date(val)
  year.value = d.getFullYear()
  month.value = d.getMonth() + 1
  monthMenu.value = false
}

function shiftMonth(delta) {
  let m = month.value - 1 + delta
  let y = year.value
  if (m < 0) { m = 11; y -= 1 }
  if (m > 11) { m = 0; y += 1 }
  year.value = y
  month.value = m + 1
  monthPicker.value = `${y}-${String(m + 1).padStart(2, '0')}`
}

// ---------- Сотрудник (автокомплит с серверным поиском) ----------
const employeeItems = ref([])
const selectedEmployee = ref(null)
const searchLoading = ref(false)
let searchTimer = null

async function fetchEmployees(q = '') {
  searchLoading.value = true
  try {
    const { data } = await api.get('/tabels/search/employees', { params: { q, limit: 50 } })
    employeeItems.value = (data || []).map(e => ({
      id: e.id,
      full_name: e.full_name,
      tab_number: e.tab_number,
      title: e.department_name ? `${e.full_name} — ${e.department_name}` : e.full_name
    }))
  } catch (e) {
    employeeItems.value = []
  } finally {
    searchLoading.value = false
  }
}

// Серверный поиск с дебаунсом (300 мс)
function onSearchInput(q) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchEmployees(q || ''), 300)
}

watch(selectedEmployee, (emp) => {
  // Если выбор сбросили через input — ищем заново
  if (!emp) fetchEmployees('')
})

const employeeTitle = computed(() => selectedEmployee.value?.full_name || '')

// ---------- Загрузка проходов ----------
const events = ref([])
const loading = ref(false)
const error = ref('')

async function loadPasses() {
  error.value = ''
  events.value = []
  if (!selectedEmployee.value || !selectedEmployee.value.id) return
  loading.value = true
  try {
    const { data } = await api.get('/api/turnstile/pass-log', {
      params: {
        year: year.value,
        month: month.value,
        employee_id: selectedEmployee.value.id
      }
    })
    events.value = data.events || []
  } catch (e) {
    if (e.response?.status === 403) {
      error.value = 'Нет доступа к этому сотруднику (права выдаёт администратор).'
    } else if (e.response?.status === 404) {
      error.value = 'Сотрудник не найден.'
    } else {
      error.value = 'Не удалось загрузить проходы: ' +
        (e.response?.data?.detail || e.message)
    }
  } finally {
    loading.value = false
  }
}

// Автозагрузка при смене месяца или сотрудника
watch([year, month], () => { loadPasses() })
watch(selectedEmployee, () => { loadPasses() })

onMounted(() => {
  fetchEmployees('')
})

// ---------- Форматирование / строки таблицы ----------
function pad(n) { return String(n).padStart(2, '0') }

function parseDT(iso) { return new Date(iso) }

function fmtDate(iso) {
  const d = parseDT(iso)
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`
}
function fmtTime(iso) {
  const d = parseDT(iso)
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const tableRows = computed(() => {
  const rows = []
  let dayIndex = -1
  let lastDateKey = null
  events.value.forEach((ev) => {
    const d = parseDT(ev.datetime)
    const dateKey = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
    const isFirstOfDay = dateKey !== lastDateKey
    if (isFirstOfDay) {
      dayIndex += 1
      lastDateKey = dateKey
    }
    const dow = d.getDay()
    rows.push({
      event: ev,
      dayIndex,
      isFirstOfDay,
      dateStr: fmtDate(ev.datetime),
      weekdayStr: WEEKDAYS[dow],
      weekend: dow === 0 || dow === 6,
      timeStr: fmtTime(ev.datetime)
    })
  })
  return rows
})

const inCount = computed(() => events.value.filter(e => e.event_type === 'in').length)
const outCount = computed(() => events.value.filter(e => e.event_type === 'out').length)
const shiftCount = computed(() => events.value.filter(e => e.event_type === 'shift').length)
</script>

<style scoped>
.passes-table :deep(thead th) {
  background-color: #2d5a3d !important;
  color: white !important;
}
/* Чередующаяся подсветка дней (группировка по дням) */
.day-alt {
  background-color: rgba(45, 90, 61, 0.045);
}
/* Визуальное разделение нового дня */
.new-day td {
  border-top: 2px solid rgba(45, 90, 61, 0.35) !important;
}
.text-orange {
  color: #e65100;
}
</style>
