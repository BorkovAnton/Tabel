<template>
  <v-container fluid class="pa-6">
    <!-- Заголовок -->
    <h1 class="text-h4 font-weight-bold mb-6">Расчёт и исправление событий проходной</h1>

    <!-- Фильтры -->
    <v-card class="mb-6" elevation="2">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="dateFrom"
              label="Дата начала"
              type="date"
              variant="outlined"
              prepend-inner-icon="mdi-calendar"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="dateTo"
              label="Дата окончания"
              type="date"
              variant="outlined"
              prepend-inner-icon="mdi-calendar"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4" class="d-flex align-end">
            <v-btn
              color="primary"
              size="large"
              class="flex-grow-1"
              @click="loadIssues"
              :loading="loading"
              prepend-icon="mdi-refresh"
            >
              Обновить
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Статистика -->
    <v-row class="mb-6">
      <v-col cols="12" md="3">
        <v-card elevation="2" color="red">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Нераспознанных ФИО</div>
            <div class="text-h3 font-weight-bold">{{ stats.unrecognized }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="orange">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Пропущенных отметок</div>
            <div class="text-h3 font-weight-bold">{{ stats.missing }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="yellow">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Дубликатов</div>
            <div class="text-h3 font-weight-bold">{{ stats.duplicates }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="blue">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Длинных смен</div>
            <div class="text-h3 font-weight-bold">{{ stats.longShifts }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Вкладки -->
    <v-card elevation="2">
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="unrecognized">
          <v-icon start>mdi-account-question</v-icon>
          Нераспознанные ФИО
        </v-tab>
        <v-tab value="missing">
          <v-icon start>mdi-clock-alert</v-icon>
          Пропущенные отметки
        </v-tab>
        <v-tab value="duplicates">
          <v-icon start>mdi-content-duplicate</v-icon>
          Дубликаты
        </v-tab>
        <v-tab value="shifts">
          <v-icon start>mdi-weather-night</v-icon>
          Смены
        </v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="activeTab">
          <!-- Вкладка: Нераспознанные ФИО -->
          <v-window-item value="unrecognized">
            <v-data-table
              :headers="unrecognizedHeaders"
              :items="unrecognizedNames"
              :loading="loading"
              class="elevation-1"
            >
              <template v-slot:item.actions="{ item }">
                <v-btn
                  color="primary"
                  size="small"
                  @click="openLinkDialog(item)"
                  prepend-icon="mdi-link"
                >
                  Связать
                </v-btn>
              </template>
            </v-data-table>
          </v-window-item>

          <!-- Вкладка: Пропущенные отметки -->
          <v-window-item value="missing">
            <v-data-table
              :headers="missingHeaders"
              :items="missingEntries"
              :loading="loading"
              class="elevation-1"
            >
              <template v-slot:item.actions="{ item }">
                <v-btn
                  color="success"
                  size="small"
                  @click="openAddEntryDialog(item)"
                  prepend-icon="mdi-plus"
                >
                  Добавить
                </v-btn>
              </template>
            </v-data-table>
          </v-window-item>

          <!-- Вкладка: Дубликаты (с чекбоксами) -->
          <v-window-item value="duplicates">
            <div class="d-flex justify-space-between align-center mb-4">
              <v-btn
                color="error"
                @click="deleteSelected"
                :disabled="selectedDuplicates.length === 0"
                :loading="deleting"
                prepend-icon="mdi-delete"
              >
                Удалить выбранные ({{ selectedDuplicates.length }})
              </v-btn>
              <div class="text-subtitle-2 text-grey">
                Всего дубликатов: {{ duplicates.length }}
              </div>
            </div>

            <v-data-table
              v-model="selectedDuplicates"
              :headers="duplicateHeaders"
              :items="duplicates"
              :loading="loading"
              show-select
              item-value="id"
              class="elevation-1"
            >
              <template v-slot:item.datetime="{ item }">
                {{ formatDate(item.datetime) }}
              </template>
              <template v-slot:item.event_type="{ item }">
                <v-chip :color="item.event_type === 'in' ? 'green' : 'red'" size="small">
                  {{ item.event_type === 'in' ? 'Вход' : 'Выход' }}
                </v-chip>
              </template>
            </v-data-table>
          </v-window-item>

          <!-- Вкладка: Смены (пары вход-выход, включая ночные через полночь) -->
          <v-window-item value="shifts">
            <div class="text-caption text-grey mb-2">
              Ночные смены (вход после 20:00, выход до 12:00 следующего дня) связываются
              в одну смену и выделяются голубым фоном с иконкой 🌙.
            </div>
            <v-data-table
              :headers="shiftHeaders"
              :items="shifts"
              :loading="loading"
              :row-class="shiftRowClass"
              class="elevation-1"
            >
              <template v-slot:item.date="{ item }">
                <span>{{ formatRuDate(item.date) }}</span>
                <span v-if="item.is_night" class="night-badge ml-1" title="Ночная смена">🌙</span>
              </template>
              <template v-slot:item.shift_times="{ item }">
                <div class="text-body-2">Вход: {{ item.first_in || '—' }}</div>
                <div class="text-body-2">Выход: {{ item.last_out || '—' }}</div>
              </template>
              <template v-slot:item.duration_hours="{ item }">
                {{ item.duration_hours != null ? `${item.duration_hours} ч` : '—' }}
              </template>
              <template v-slot:item.status="{ item }">
                <v-chip :color="item.ok ? 'green' : 'red'" size="small">
                  <v-icon start size="small">{{ item.ok ? 'mdi-check' : 'mdi-close' }}</v-icon>
                  {{ item.status }}
                </v-chip>
              </template>
            </v-data-table>
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>

    <!-- Диалог связывания ФИО -->
    <v-dialog v-model="linkDialog" max-width="700">
      <v-card>
        <v-card-title>Связать «{{ selectedName?.raw_name }}» ({{ selectedName?.count }} записей)</v-card-title>
        <v-card-text>
          <v-checkbox
            v-model="applyToAll"
            label="Применить ко всем записям с этим ФИО"
            color="primary"
            hide-details
            class="mb-4"
          ></v-checkbox>

          <transition name="fade" mode="out-in">
            <!-- Режим 1: один сотрудник на все записи -->
            <div v-if="applyToAll" key="all">
              <v-autocomplete
                v-model="selectedEmployee"
                :items="employeeSearchResults"
                item-title="display"
                item-value="id"
                label="Выберите сотрудника"
                hint="Начните вводить фамилию (минимум 2 символа)"
                persistent-hint
                variant="outlined"
                density="comfortable"
                :loading="employeeSearchLoading"
                no-filter
                clearable
                hide-no-data
                return-object
                @update:model-value="onEmployeeSelected"
                @update:search="onEmployeeSearchInput"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props" :title="item.raw.display"></v-list-item>
                </template>
              </v-autocomplete>
            </div>

            <!-- Режим 2: выбор сотрудника для каждого дня отдельно -->
            <div v-else key="days">
              <div class="text-caption text-grey mb-2">
                Выберите сотрудника для каждого дня. Дни без выбора останутся нераспознанными.
              </div>
              <div v-if="unrecognizedDaysLoading" class="d-flex justify-center pa-6">
                <v-progress-circular indeterminate color="primary"></v-progress-circular>
              </div>
              <v-alert v-else-if="unrecognizedDays.length === 0" type="info" density="compact">
                Нет проходов этого ФИО в базе.
              </v-alert>
              <div v-else style="max-height: 380px; overflow-y: auto;">
                <v-row
                  v-for="day in unrecognizedDays"
                  :key="day.date"
                  dense
                  align="center"
                  class="mb-1"
                >
                  <v-col cols="12" md="5" class="py-0">
                    <div class="text-body-2 font-weight-medium">{{ formatRuDate(day.date) }}</div>
                    <div class="text-caption text-grey">
                      Вход: {{ day.first_in || '—' }} / Выход: {{ day.last_out || '—' }} · {{ day.count }} событ.
                    </div>
                  </v-col>
                  <v-col cols="12" md="7" class="py-0">
                    <v-autocomplete
                      v-model="day.employee"
                      :items="getDayResults(day)"
                      item-title="display"
                      item-value="id"
                      label="Сотрудник за этот день"
                      variant="outlined"
                      density="compact"
                      hide-details
                      :loading="day.searching"
                      no-filter
                      clearable
                      hide-no-data
                      return-object
                      @update:search="(q) => onDaySearch(day, q)"
                    >
                      <template #item="{ props, item }">
                        <v-list-item v-bind="props" :title="item.raw.display"></v-list-item>
                      </template>
                    </v-autocomplete>
                  </v-col>
                </v-row>
              </div>
            </div>
          </transition>

          <v-alert v-if="linkError" type="error" density="compact" class="mt-3">{{ linkError }}</v-alert>
          <v-alert v-if="linkWarning" type="warning" density="compact" class="mt-3">{{ linkWarning }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="linkDialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="linkEmployee" :loading="linking">
            Связать
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог добавления отметки -->
    <v-dialog v-model="addEntryDialog" max-width="500">
      <v-card>
        <v-card-title>Добавить пропущенную отметку</v-card-title>
        <v-card-text>
          <p class="mb-4">
            <strong>{{ selectedMissing?.employee_name }}</strong>
            <br>
            Дата: {{ selectedMissing?.date }}
            <br>
            Проблема: {{ selectedMissing?.issue }}
          </p>
          <v-alert
            v-if="addError"
            type="error"
            density="compact"
            class="mb-3"
            closable
          >{{ addError }}</v-alert>
          <v-alert
            v-if="addSuccess"
            type="success"
            density="compact"
            class="mb-3"
            closable
          >{{ addSuccess }}</v-alert>
          <v-row dense class="mb-1">
            <v-col cols="7">
              <v-text-field
                v-model="newEntryDate"
                label="Дата"
                type="date"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </v-col>
            <v-col cols="5">
              <v-text-field
                v-model="newEntryTime"
                label="Время"
                type="time"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </v-col>
          </v-row>
          <v-select
            v-model="newEntryType"
            :items="[
              { title: 'Вход', value: 'in' },
              { title: 'Выход', value: 'out' }
            ]"
            item-title="title"
            item-value="value"
            label="Тип отметки"
            variant="outlined"
          ></v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="addEntryDialog = false">Отмена</v-btn>
          <v-btn color="success" @click="addMissingEntry" :loading="adding">
            Добавить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Зелёное уведомление об успешном добавлении отметки -->
    <v-snackbar v-model="showAddSnackbar" :timeout="3000" color="success">
      {{ addSuccess }}
      <template #actions>
        <v-btn variant="text" @click="showAddSnackbar = false">Закрыть</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api'

const loading = ref(false)
const linking = ref(false)
const adding = ref(false)
const deleting = ref(false)

const dateFrom = ref(new Date().toISOString().split('T')[0])
const dateTo = ref(new Date().toISOString().split('T')[0])
const activeTab = ref('unrecognized')

const stats = ref({
  unrecognized: 0,
  missing: 0,
  duplicates: 0,
  longShifts: 0
})

const unrecognizedNames = ref([])
const missingEntries = ref([])
const duplicates = ref([])
const shifts = ref([])
const employees = ref([])
const selectedDuplicates = ref([]) // ← Новое: выбранные дубликаты

const linkDialog = ref(false)
const addEntryDialog = ref(false)
const addSuccess = ref('')
const showAddSnackbar = ref(false)

const selectedName = ref(null)
const selectedMissing = ref(null)
const selectedEmployeeId = ref(null)
const applyToAll = ref(true)
const newEntryDate = ref('')
const newEntryTime = ref('')
const addError = ref('')
const newEntryType = ref('in')
const linkError = ref('')
const linkWarning = ref('')

// Режим «по дням»: список проходов нераспознанного ФИО, сгруппированных по датам
const unrecognizedDays = ref([])
const unrecognizedDaysLoading = ref(false)

// ===== Поиск сотрудника в диалоге «Связать ФИО с сотрудником» =====
// v-autocomplete управляется вручную: поиск по началу строки (фамилия),
// минимум 2 символа, debounce 300 мс, максимум 10 результатов.
const MIN_SEARCH_LENGTH = 2
const MAX_RESULTS = 10
const DEBOUNCE_MS = 300

const selectedEmployee = ref(null) // выбранный сотрудник (объект { id, display, ... })
const employeeSearchQuery = ref('')
const employeeSearchResults = ref([])
const employeeSearchLoading = ref(false)
let employeeSearchTimer = null

// «Борков Антон Петрович» → «Борков А.П.»
function shortFullName(fullName) {
  const parts = (fullName || '').trim().split(/\s+/)
  if (parts.length < 2) return fullName || ''
  const last = parts[0]
  const initials = parts.slice(1).map(p => (p[0] || '').toUpperCase() + '.').join('')
  return `${last} ${initials}`
}

function employeeDisplay(emp) {
  return `${shortFullName(emp.full_name)} — ${emp.tab_number} — ${emp.department_name || 'без подразделения'}`
}

// Сортировка: точное совпадение → начало строки → остальные
function sortEmployees(list, query) {
  const q = query.toLowerCase().trim()
  const norm = s => (s || '').toLowerCase().replace(/ё/g, 'е')
  const nq = norm(q)
  return [...list].sort((a, b) => {
    const fa = norm(a.full_name)
    const fb = norm(b.full_name)
    const exactA = fa === nq ? 0 : 1
    const exactB = fb === nq ? 0 : 1
    if (exactA !== exactB) return exactA - exactB
    const prefA = fa.startsWith(nq) ? 0 : 1
    const prefB = fb.startsWith(nq) ? 0 : 1
    if (prefA !== prefB) return prefA - prefB
    return fa.localeCompare(fb, 'ru')
  })
}

function runEmployeeSearch() {
  const q = employeeSearchQuery.value.trim()
  employeeSearchLoading.value = true
  if (q.length < MIN_SEARCH_LENGTH) {
    // При пустом/коротком запросе — список пуст (не показываем всех сразу)
    employeeSearchResults.value = []
    employeeSearchLoading.value = false
    return
  }
  const nq = q.toLowerCase().replace(/ё/g, 'е')
  const matched = employees.value.filter(e =>
    (e.full_name || '').toLowerCase().replace(/ё/g, 'е').startsWith(nq)
  )
  employeeSearchResults.value = sortEmployees(matched, q)
    .slice(0, MAX_RESULTS)
    .map(e => ({ id: e.id, display: employeeDisplay(e), full_name: e.full_name }))
  employeeSearchLoading.value = false
}

function onEmployeeSearchInput(val) {
  employeeSearchQuery.value = val || ''
  clearTimeout(employeeSearchTimer)
  employeeSearchTimer = setTimeout(runEmployeeSearch, DEBOUNCE_MS)
}

function onEmployeeSelected(emp) {
  // v-model возвращает объект (return-object) — сохраняем id для отправки на бэкенд
  selectedEmployeeId.value = emp && typeof emp === 'object' ? emp.id : (emp || null)
}

// ===== Поиск сотрудника в режиме «по дням» (отдельный autocomplete на каждый день) =====
function searchEmployeesForQuery(q) {
  const query = (q || '').trim()
  if (query.length < MIN_SEARCH_LENGTH) return []
  const nq = query.toLowerCase().replace(/ё/g, 'е')
  const matched = employees.value.filter(e =>
    (e.full_name || '').toLowerCase().replace(/ё/g, 'е').startsWith(nq)
  )
  return sortEmployees(matched, query)
    .slice(0, MAX_RESULTS)
    .map(e => ({ id: e.id, display: employeeDisplay(e), full_name: e.full_name }))
}

function onDaySearch(day, q) {
  day.query = q || ''
  day.searching = true
  clearTimeout(day.timer)
  day.timer = setTimeout(() => {
    day.results = searchEmployeesForQuery(day.query)
    day.searching = false
  }, DEBOUNCE_MS)
}

function getDayResults(day) {
  // Показываем результаты поиска + уже выбранного сотрудника (чтобы v-autocomplete
  // мог отобразить выбранный объект, даже если он не входит в текущие 10 результатов)
  const results = day.results || []
  if (day.employee && !results.some(r => r.id === day.employee.id)) {
    return [day.employee, ...results]
  }
  return results
}

function formatRuDate(isoDate) {
  if (!isoDate) return ''
  const d = new Date(isoDate + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

async function loadUnrecognizedDays(rawName) {
  unrecognizedDaysLoading.value = true
  unrecognizedDays.value = []
  try {
    const response = await api.get('/api/turnstile-fix/unrecognized-events', {
      params: { raw_name: rawName }
    })
    unrecognizedDays.value = response.data.map(d => ({
      date: d.date,
      count: d.count,
      first_in: d.first_in,
      last_out: d.last_out,
      employee: null,
      results: [],
      query: '',
      searching: false,
      timer: null,
    }))
  } catch (e) {
    console.error('Ошибка загрузки проходов по датам:', e)
    linkError.value = 'Не удалось загрузить список проходов по датам'
  } finally {
    unrecognizedDaysLoading.value = false
  }
}

const unrecognizedHeaders = [
  { title: 'ФИО', key: 'raw_name' },
  { title: 'Количество записей', key: 'count' },
  { title: 'Действия', key: 'actions', sortable: false }
]

const missingHeaders = [
  { title: 'Сотрудник', key: 'employee_name' },
  { title: 'Дата', key: 'date' },
  { title: 'Существующая отметка', key: 'existing_info' },
  { title: 'Проблема', key: 'issue' },
  { title: 'Действия', key: 'actions', sortable: false }
]

const duplicateHeaders = [
  { title: 'ID', key: 'id', width: '80px' },
  { title: 'Сотрудник ID', key: 'employee_id', width: '120px' },
  { title: 'Дата и время', key: 'datetime', width: '180px' },
  { title: 'Тип', key: 'event_type', width: '100px' },
  { title: 'Дубликат ID', key: 'duplicate_of', width: '120px' }
]

const shiftHeaders = [
  { title: 'Сотрудник', key: 'employee_name' },
  { title: 'Дата', key: 'date', width: '140px' },
  { title: 'Смена', key: 'shift_times', width: '220px' },
  { title: 'Длительность', key: 'duration_hours', width: '130px' },
  { title: 'Статус', key: 'status', width: '150px' }
]

// Голубой фон для ночных смен
function shiftRowClass({ item }) {
  return item.is_night ? 'night-shift-row' : ''
}

async function loadEmployees() {
  try {
    const response = await api.get('/employees/')
    employees.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки сотрудников:', e)
  }
}

async function loadIssues() {
  loading.value = true
  
  try {
    // Загружаем нераспознанные ФИО
    const unrecognizedResponse = await api.get('/api/turnstile-fix/unrecognized-names')
    unrecognizedNames.value = unrecognizedResponse.data
    stats.value.unrecognized = unrecognizedResponse.data.length
    
    // Загружаем пропущенные отметки
    const missingEntryResponse = await api.get('/api/turnstile-fix/issues', {
      params: { date_from: dateFrom.value, date_to: dateTo.value, issue_type: 'missing_entry' }
    })
    const missingExitResponse = await api.get('/api/turnstile-fix/issues', {
      params: { date_from: dateFrom.value, date_to: dateTo.value, issue_type: 'missing_exit' }
    })
    
    const allMissing = [...missingEntryResponse.data, ...missingExitResponse.data]
    
    missingEntries.value = allMissing.map(item => {
      const emp = employees.value.find(e => e.id === item.employee_id)
      // Убираем дубликаты времени через Set и сортируем
      const uniqueTimes = item.existing_time 
        ? [...new Set(item.existing_time.split(' | '))].sort().join(' | ')
        : ''
      
      const existingInfo = uniqueTimes
        ? `${item.existing_type === 'in' ? 'Вход' : 'Выход'}: ${uniqueTimes}`
        : 'Нет данных'
      
      return {
        ...item,
        employee_name: emp?.full_name || `ID: ${item.employee_id}`,
        existing_info: existingInfo
      }
    })
    
    stats.value.missing = allMissing.length
    
    // Загружаем дубликаты
    const duplicateResponse = await api.get('/api/turnstile-fix/issues', {
      params: { date_from: dateFrom.value, date_to: dateTo.value, issue_type: 'duplicate' }
    })
    duplicates.value = duplicateResponse.data
    stats.value.duplicates = duplicateResponse.data.length
    
    // Загружаем смены (пары вход-выход с учётом ночных через полночь)
    try {
      const shiftsResponse = await api.get('/api/turnstile-fix/shifts', {
        params: { date_from: dateFrom.value, date_to: dateTo.value }
      })
      shifts.value = shiftsResponse.data
      stats.value.longShifts = shiftsResponse.data.filter(s => s.duration_hours != null && s.duration_hours > 12).length
    } catch (shiftsErr) {
      console.error('Ошибка загрузки смен:', shiftsErr)
      shifts.value = []
    }

  } catch (e) {
    console.error('Ошибка загрузки проблем:', e)
  } finally {
    loading.value = false
  }
}

function openLinkDialog(item) {
  selectedName.value = item
  selectedEmployeeId.value = null
  selectedEmployee.value = null
  employeeSearchQuery.value = ''
  employeeSearchResults.value = []
  applyToAll.value = true
  linkError.value = ''
  linkWarning.value = ''
  unrecognizedDays.value = []
  linkDialog.value = true
}

// При снятии галочки «Применить ко всем» — загружаем проходы по дням (без ошибки)
watch(applyToAll, (val) => {
  linkError.value = ''
  linkWarning.value = ''
  if (!val && selectedName.value && unrecognizedDays.value.length === 0 && !unrecognizedDaysLoading.value) {
    loadUnrecognizedDays(selectedName.value.raw_name)
  }
})

async function linkEmployee() {
  linkError.value = ''
  linkWarning.value = ''

  if (applyToAll.value) {
    // Режим «ко всем записям»: одно поле выбора сотрудника
    if (!selectedEmployeeId.value) {
      linkError.value = 'Выберите сотрудника'
      return
    }
    linking.value = true
    try {
      await api.patch('/api/turnstile-fix/bulk-link', {
        raw_name: selectedName.value.raw_name,
        employee_id: selectedEmployeeId.value
      })
      linkDialog.value = false
      await loadIssues()
    } catch (e) {
      console.error('Ошибка связывания:', e)
      linkError.value = e?.response?.data?.detail || 'Ошибка при связывании'
    } finally {
      linking.value = false
    }
    return
  }

  // Режим «по дням»: собираем привязки для дней, где выбран сотрудник
  const items = unrecognizedDays.value
    .filter(d => d.employee)
    .map(d => ({ date: d.date, employee_id: d.employee.id }))

  if (items.length === 0) {
    linkError.value = 'Не выбран сотрудник ни для одного дня'
    return
  }

  const skipped = unrecognizedDays.value.length - items.length
  if (skipped > 0) {
    linkWarning.value = `Пропущено дней без выбора: ${skipped} — они останутся нераспознанными`
  }

  linking.value = true
  try {
    await api.post('/api/turnstile-fix/link-unrecognized', {
      raw_name: selectedName.value.raw_name,
      items
    })
    if (skipped === 0) {
      // Всё связано — закрываем диалог
      linkDialog.value = false
    } else {
      // Обновляем список дней, чтобы показать оставшиеся непровязанные
      await loadUnrecognizedDays(selectedName.value.raw_name)
      setTimeout(() => { linkWarning.value = '' }, 5000)
    }
    await loadIssues()
  } catch (e) {
    console.error('Ошибка связывания:', e)
    linkError.value = e?.response?.data?.detail || 'Ошибка при связывании'
  } finally {
    linking.value = false
  }
}

function openAddEntryDialog(item) {
  selectedMissing.value = item
  addError.value = ''
  const baseDate = item.date
  const suggestedTime = item.existing_type === 'in' ? '17:00' : '08:00'
  newEntryDate.value = baseDate
  newEntryTime.value = suggestedTime
  newEntryType.value = item.existing_type === 'in' ? 'out' : 'in'
  addEntryDialog.value = true
}

async function addMissingEntry() {
  if (!selectedMissing.value || !selectedMissing.value.employee_id) {
    addError.value = 'Не выбран сотрудник для добавления отметки'
    return
  }
  if (!newEntryDate.value || !newEntryTime.value || !newEntryType.value) {
    addError.value = 'Заполните дату, время и тип отметки'
    return
  }

  // Собираем ISO-строку из отдельных полей даты и времени.
  const time = newEntryTime.value.length === 5 ? `${newEntryTime.value}:00` : newEntryTime.value
  const dt = `${newEntryDate.value}T${time}`

  adding.value = true
  addError.value = ''
  try {
    const response = await api.post('/api/turnstile-fix/fix-missing', {
      employee_id: selectedMissing.value.employee_id,
      datetime: dt,
      event_type: newEntryType.value
    })
    // Отметка реально сохранена на сервере — закрываем диалог и обновляем списки.
    addEntryDialog.value = false
    await loadIssues()
    // Показываем зелёное уведомление об успехе (автоскрытие через snackbar).
    addSuccess.value = 'Отметка успешно добавлена'
    showAddSnackbar.value = true
    console.log('Отметка добавлена:', response.data)
  } catch (e) {
    console.error('Ошибка добавления отметки:', e)
    const status = e?.response?.status
    const detail = e?.response?.data?.detail
    if (status === 422) {
      addError.value = 'Проверьте формат даты и времени'
    } else if (status === 404) {
      addError.value = typeof detail === 'string' ? detail : 'Сотрудник не найден на сервере'
    } else if (status === 409) {
      addError.value = detail || 'Такое событие уже существует'
    } else if (status === 400) {
      addError.value = detail || 'Некорректные данные отметки'
    } else {
      addError.value = 'Ошибка при добавлении отметки' + (typeof detail === 'string' ? `: ${detail}` : '')
    }
  } finally {
    adding.value = false
  }
}

// ← НОВАЯ ФУНКЦИЯ: Массовое удаление дубликатов
async function deleteSelected() {
  if (selectedDuplicates.value.length === 0) return

  if (!confirm(`Вы уверены, что хотите удалить ${selectedDuplicates.value.length} дубликатов?`)) {
    return
  }

  deleting.value = true
  try {
    const deletePromises = selectedDuplicates.value.map(id =>
      api.delete(`/api/turnstile-fix/${id}`)
    )
    await Promise.all(deletePromises)

    selectedDuplicates.value = [] // Очищаем выбор
    await loadIssues() // Перезагружаем таблицу
  } catch (e) {
    console.error('Ошибка массового удаления:', e)
    alert('Ошибка при удалении дубликатов')
  } finally {
    deleting.value = false
  }
}

// ← НОВАЯ ФУНКЦИЯ: Форматирование даты
function formatDate(datetime) {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  loadEmployees()
  loadIssues()
})
</script>

<style>
/* Глобальные стили для чекбоксов в таблице */

/* Основной контейнер чекбокса */
.v-data-table .v-checkbox-btn {
  opacity: 1 !important;
}

/* Рамка чекбокса */
.v-data-table .v-checkbox-btn .v-selection-control__wrapper {
  border: 2px solid #2e7d32 !important;
  border-radius: 4px !important;
  background-color: white !important;
}

/* Иконка (круг внутри) */
.v-data-table .v-checkbox-btn .v-selection-control__input {
  color: #2e7d32 !important;
  background-color: transparent !important;
  width: 20px !important;
  height: 20px !important;
}

/* Выбранный чекбокс — зеленый фон */
.v-data-table .v-checkbox-btn.v-selection-control--dirty .v-selection-control__wrapper {
  background-color: #4caf50 !important;
  border-color: #2e7d32 !important;
}

/* Галочка в выбранном чекбоксе — белая */
.v-data-table .v-checkbox-btn.v-selection-control--dirty .v-selection-control__input .v-icon {
  color: white !important;
  opacity: 1 !important;
}

/* Hover эффект */
.v-data-table .v-checkbox-btn:hover .v-selection-control__wrapper {
  border-color: #1b5e20 !important;
  background-color: rgba(76, 175, 80, 0.1) !important;
}

/* Чекбокс в заголовке таблицы */
.v-data-table thead .v-checkbox-btn .v-selection-control__wrapper {
  border: 2px solid #2e7d32 !important;
}

/* Увеличиваем специфичность для гарантированного применения */
.v-application .v-data-table .v-checkbox-btn.v-selection-control--dirty {
  color: #4caf50 !important;
}

/* Ночные смены — голубой фон строки */
.v-data-table tr.night-shift-row td {
  background-color: #e3f2fd !important;
}
.v-data-table tr.night-shift-row:hover td {
  background-color: #d1e7fb !important;
}
.night-badge {
  font-size: 14px;
}
</style>