<template>
  <v-container fluid>
    <h1 class="text-h4 mb-4">Увольнительные записки</h1>

    <!-- Фильтры -->
    <v-card class="mb-4 pa-4">
      <v-row>
        <v-col cols="12" md="3">
          <v-select
            v-model="filterMonth"
            :items="monthItems"
            item-title="title"
            item-value="value"
            label="Месяц"
            clearable
            density="compact"
            hide-details
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filterYear"
            :items="years"
            label="Год"
            clearable
            density="compact"
            hide-details
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-autocomplete
            v-model="filterDepartment"
            :items="departments"
            item-title="name"
            item-value="id"
            label="Подразделение"
            variant="outlined"
            clearable
            return-object
          />
        </v-col>
        <v-col cols="12" md="3" class="d-flex align-end" style="gap: 8px;">
          <v-btn color="primary" prepend-icon="mdi-magnify" @click="loadNotes" class="mr-2">
            Найти
          </v-btn>
          <v-btn color="success" prepend-icon="mdi-plus" @click="openCreateDialog">
            Создать записку
          </v-btn>
        </v-col>
      </v-row>
    </v-card>

    <v-alert v-if="notes.length === 0 && !loading" type="info" variant="tonal" class="mb-4">
      Увольнительных записок не найдено. Нажмите «Создать записку», чтобы добавить первую.
    </v-alert>

    <!-- Список записок -->
    <v-card v-for="note in notes" :key="note.id" class="mb-4">
      <v-card-title class="d-flex justify-space-between align-center flex-wrap">
        <div>
          <strong>Период:</strong> {{ formatPeriod(note.period_start, note.period_end) }}
          <span v-if="note.department_name" class="ml-4">
            <strong>Подразделение:</strong> {{ note.department_name }}
          </span>
        </div>
        <div class="d-flex align-center">
          <v-chip color="primary" class="mr-2">
            Всего часов: {{ note.total_hours }}
          </v-chip>
          <CustomEditButton @click="openEditDialog(note)" />
          <CustomDeleteButton @click="deleteNote(note.id)" />
        </div>
      </v-card-title>

      <v-card-text v-if="note.comment">
        <span class="text-grey-darken-1"><strong>Комментарий:</strong> {{ note.comment }}</span>
      </v-card-text>

      <v-card-text>
        <!-- Таблица увольнительной записки -->
        <div style="overflow-x: auto;">
          <table class="dismissal-table">
            <thead>
              <tr>
                <th class="col-num">№</th>
                <th class="col-fio">Ф.И.О.</th>
                <th class="col-dept">Подразделение</th>
                <th v-for="day in getNoteDays(note)" :key="day" class="col-day">
                  {{ day }}
                </th>
                <th class="col-total col-work">По работе</th>
                <th class="col-total col-personal">Личная</th>
                <th class="col-total col-undefined">Неопределённо</th>
                <th class="col-total col-grand-total">Итого</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(entry, idx) in note.entries" :key="entry.id">
                <td class="col-num">{{ idx + 1 }}</td>
                <td class="col-fio">
                  <div>{{ entry.employee_name }}</div>
                  <div class="text-caption text-grey">Таб. {{ entry.employee_tab_number }}</div>
                </td>
                <td class="col-dept">{{ entry.department_name }}</td>
                <td
                  v-for="day in getNoteDays(note)"
                  :key="day"
                  class="col-day"
                  :class="getDayCellClass(entry, day)"
                  title="Нажмите, чтобы указать время ухода и возврата"
                  @click="openDayDialog(entry, day)"
                >
                  <template v-if="getDayRecord(entry, day)">
                    <div v-if="getDayRecord(entry, day).time_out" class="day-time">
                      &rarr; {{ getDayRecord(entry, day).time_out }}
                    </div>
                    <div v-if="getDayRecord(entry, day).time_in" class="day-time">
                      &larr; {{ getDayRecord(entry, day).time_in }}
                    </div>
                    <div v-if="getDayRecord(entry, day).hours > 0" class="day-hours">
                      {{ getDayRecord(entry, day).hours }}ч
                    </div>
                  </template>
                </td>
                <td class="col-total col-work"><strong>{{ entry.work_hours || 0 }}</strong></td>
                <td class="col-total col-personal"><strong>{{ entry.personal_hours || 0 }}</strong></td>
                <td class="col-total col-undefined"><strong>{{ entry.undefined_hours || 0 }}</strong></td>
                <td class="col-total col-grand-total"><strong>{{ entry.total_hours }}</strong></td>
              </tr>
              <tr v-if="note.entries.length === 0">
                <td :colspan="getNoteDays(note).length + 7" class="text-center py-4 text-grey">
                  Нет сотрудников. Нажмите «Редактировать», чтобы добавить.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </v-card-text>
    </v-card>

    <!-- Диалог создания/редактирования записки -->
    <v-dialog v-model="showNoteDialog" max-width="1200" persistent>
      <v-card>
        <v-card-title>{{ isEditing ? 'Редактировать записку' : 'Новая увольнительная записка' }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="3">
              <v-select
                v-model="form.month"
                :items="monthItems"
                item-title="title"
                item-value="value"
                label="Месяц"
                variant="outlined"
                density="compact"
                hide-details
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="form.year"
                :items="years"
                label="Год"
                variant="outlined"
                density="compact"
                hide-details
              />
            </v-col>
            <v-col cols="12" md="4">
              <v-autocomplete
                v-model="form.department_id"
                :items="departments"
                item-title="name"
                item-value="id"
                label="Подразделение"
                variant="outlined"
                clearable
                return-object
              />
            </v-col>
          </v-row>

          <v-alert v-if="periodError" type="error" variant="tonal" class="mb-2">
            {{ periodError }}
          </v-alert>

          <v-textarea
            v-model="form.comment"
            label="Комментарий"
            variant="outlined"
            rows="2"
          />

          <!-- Список сотрудников -->
          <div class="mt-4">
            <div class="d-flex align-center mb-2">
              <h3>Сотрудники</h3>
              <v-spacer />
              <v-btn color="primary" prepend-icon="mdi-account-plus" @click="openAddEmployeeDialog">
                Добавить сотрудника
              </v-btn>
            </div>

            <!-- Таблица увольнения (как в табеле): клик по ячейке дня — ввод времени -->
            <div v-if="form.entries.length > 0" style="overflow-x: auto;">
              <table class="dismissal-table">
                <thead>
                  <tr>
                    <th class="col-num">№</th>
                    <th class="col-fio">Ф.И.О.</th>
                    <th class="col-dept">Подразделение</th>
                    <th v-for="day in daysInPeriod" :key="day" class="col-day">
                      {{ day }}
                    </th>
                    <th class="col-total col-work">По работе</th>
                    <th class="col-total col-personal">Личная</th>
                    <th class="col-total col-undefined">Неопределённо</th>
                    <th class="col-total col-grand-total">Итого</th>
                    <th class="col-actions">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(entry, idx) in form.entries" :key="idx">
                    <td class="col-num">{{ idx + 1 }}</td>
                    <td class="col-fio">
                      <div>{{ entry.employee_name }}</div>
                      <div class="text-caption text-grey">Таб. {{ entry.employee_tab_number }}</div>
                    </td>
                    <td class="col-dept">{{ entry.department_name }}</td>
                    <td
                      v-for="day in daysInPeriod"
                      :key="day"
                      class="col-day"
                      :class="getDayCellClass(entry, day)"
                      title="Нажмите, чтобы указать время ухода и возврата"
                      @click="openDayDialog(entry, day)"
                    >
                      <template v-if="getDayRecord(entry, day)">
                        <div v-if="getDayRecord(entry, day).time_out" class="day-time">
                          &rarr; {{ getDayRecord(entry, day).time_out }}
                        </div>
                        <div v-if="getDayRecord(entry, day).time_in" class="day-time">
                          &larr; {{ getDayRecord(entry, day).time_in }}
                        </div>
                        <div v-if="getDayRecord(entry, day).hours > 0" class="day-hours">
                          {{ getDayRecord(entry, day).hours }}ч
                        </div>
                      </template>
                    </td>
                    <td class="col-total col-work"><strong>{{ entry.work_hours || 0 }}</strong></td>
                    <td class="col-total col-personal"><strong>{{ entry.personal_hours || 0 }}</strong></td>
                    <td class="col-total col-undefined"><strong>{{ entry.undefined_hours || 0 }}</strong></td>
                    <td class="col-total col-grand-total"><strong>{{ entry.total_hours }}</strong></td>
                    <td class="col-actions">
                      <CustomDeleteButton @click="removeEntry(idx)" />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <v-alert v-else type="info" variant="tonal">
              Добавьте сотрудников через кнопку «Добавить сотрудника». Клик по ячейке дня — ввод времени ухода и возврата.
            </v-alert>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showNoteDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="saving" :disabled="!!periodError" @click="saveNote">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог добавления сотрудника (поиск) -->
    <v-dialog v-model="showAddEmployeeDialog" max-width="600">
      <v-card>
        <v-card-title>Добавить сотрудника</v-card-title>
        <v-card-text>
          <v-progress-linear v-if="employeesLoading" indeterminate color="primary" />
          <v-autocomplete
            v-model="selectedEmployee"
            :items="employees"
            item-title="full_name"
            item-value="id"
            label="Сотрудник (поиск по ФИО / таб. номеру)"
            variant="outlined"
            clearable
            return-object
            placeholder="Начните вводить фамилию..."
            no-filter
            @update:search="searchEmployees"
          >
            <template #item="{ props, item }">
              <v-list-item
                v-bind="props"
                :title="item.raw.full_name"
                :subtitle="`Таб. ${item.raw.tab_number} — ${item.raw.department_name || ''}`"
              />
            </template>
          </v-autocomplete>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showAddEmployeeDialog = false">Отмена</v-btn>
          <v-btn color="primary" :disabled="!selectedEmployee" @click="addEmployee">Добавить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог ввода времени за день -->
    <v-dialog v-model="showDayDialog" max-width="420">
      <v-card>
        <v-card-title class="text-subtitle-1">
          {{ currentEntry && currentEntry.employee_name }} — {{ currentDay }} число
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model="dayForm.time_out"
                label="Время ухода"
                type="time"
                variant="outlined"
                hint="Когда ушёл"
                persistent-hint
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="dayForm.time_in"
                label="Время возврата"
                type="time"
                variant="outlined"
                hint="Когда вернулся"
                persistent-hint
              />
            </v-col>
          </v-row>

          <div class="reason-checkboxes mt-4">
            <div class="text-subtitle-2 mb-1">Причина отсутствия:</div>
            <v-checkbox
              v-model="dayForm.reason"
              value="work"
              label="По работе"
              color="primary"
              density="compact"
              hide-details
              class="mb-1"
            />
            <v-checkbox
              v-model="dayForm.reason"
              value="personal"
              label="Личная"
              color="secondary"
              density="compact"
              hide-details
              class="mb-1"
            />
            <v-checkbox
              v-model="dayForm.reason"
              value="undefined"
              label="Неопределённо"
              color="grey"
              density="compact"
              hide-details
            />
          </div>

          <v-alert v-if="dayForm.hours > 0" type="success" variant="tonal" class="mt-2">
            Итого часов: <strong>{{ dayForm.hours }}</strong>
          </v-alert>
          <v-alert v-else-if="dayForm.time_out || dayForm.time_in" type="warning" variant="tonal" class="mt-2">
            Укажите оба времени (уход и возврат), чтобы рассчитать часы
          </v-alert>

          <div v-if="dayForm.time_out || dayForm.time_in" class="d-flex align-center mt-3" style="gap: 8px;">
            <CustomDeleteButton title="Очистить запись" @click="clearDay" />
            <span class="text-body-2">Очистить запись</span>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDayDialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveDay">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '../api'
import CustomEditButton from '../components/CustomEditButton.vue'
import CustomDeleteButton from '../components/CustomDeleteButton.vue'

const notes = ref([])
const departments = ref([])
const employees = ref([])
const employeesLoading = ref(false)
const loading = ref(false)
const filterMonth = ref(null)
const filterYear = ref(new Date().getFullYear())
const filterDepartment = ref(null)

// Месяцы/годы — как при просмотре табелей (Tabels.vue)
const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
const _now = new Date()
const years = Array.from({ length: 6 }, (_, i) => _now.getFullYear() - 3 + i)
const monthItems = monthNames.map((title, idx) => ({ title, value: idx + 1 }))

const showNoteDialog = ref(false)
const showAddEmployeeDialog = ref(false)
const showDayDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const currentNoteId = ref(null)

const selectedEmployee = ref(null)
const currentEntry = ref(null)
const currentDay = ref(null)

const form = ref({
  month: _now.getMonth() + 1,
  year: _now.getFullYear(),
  department_id: null,
  comment: '',
  entries: []
})

// Причина отсутствия по умолчанию при заполнении увольнительной записки — «Личная».
// (Сохраняется как код 'personal'; старые записи без причины тоже считаются личной.)
const DEFAULT_REASON = 'personal'

const dayForm = ref({
  time_out: '',
  time_in: '',
  reason: DEFAULT_REASON,  // 'work' | 'personal' | 'undefined'
  hours: 0
})

// Строки 'ГГГГ-ММ-ДД' начала и конца месяца (месяц передан как 1..12)
function pad2(n) {
  return String(n).padStart(2, '0')
}

function monthStartStr(year, month) {
  return `${year}-${pad2(month)}-01`
}

function monthEndStr(year, month) {
  const lastDay = new Date(year, month, 0).getDate()
  return `${year}-${pad2(month)}-${pad2(lastDay)}`
}

// Дни периода текущей редактируемой записки (для таблицы в диалоге) — весь месяц
const daysInPeriod = computed(() => {
  const m = form.value.month || (_now.getMonth() + 1)
  const y = form.value.year || _now.getFullYear()
  return buildDays(monthStartStr(y, m), monthEndStr(y, m))
})

const periodError = computed(() => '')

function buildDays(startStr, endStr) {
  if (!startStr || !endStr) return Array.from({ length: 31 }, (_, i) => i + 1)
  const start = new Date(startStr + 'T00:00:00')
  const end = new Date(endStr + 'T00:00:00')
  const days = []
  let guard = 0
  for (let d = new Date(start); d <= end && guard < 366; d.setDate(d.getDate() + 1), guard++) {
    days.push(d.getDate())
  }
  return days
}

// Дни для уже сохранённой записки (в списке)
function getNoteDays(note) {
  return buildDays(note.period_start, note.period_end)
}

async function loadNotes() {
  loading.value = true
  try {
    const params = {}
    // Фильтр по месяцу/году — как при просмотре табелей: пересечение с периодом месяца
    if (filterMonth.value && filterYear.value) {
      params.date_from = monthStartStr(filterYear.value, filterMonth.value)
      params.date_to = monthEndStr(filterYear.value, filterMonth.value)
    }
    if (filterDepartment.value) params.department_id = filterDepartment.value.id

    const { data } = await api.get('/dismissal-notes/', { params })
    notes.value = data
  } catch (e) {
    console.error('Ошибка загрузки:', e)
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  try {
    const { data } = await api.get('/departments/')
    // Плоский список подразделений (дерево разворачиваем)
    const flat = []
    const walk = (list) => {
      for (const d of list || []) {
        flat.push({ id: d.id, name: d.name })
        if (d.children && d.children.length) walk(d.children)
      }
    }
    walk(data)
    departments.value = flat
  } catch (e) {
    console.error('Ошибка загрузки подразделений:', e)
  }
}

async function searchEmployees(query) {
  if (!query || query.length < 2) return
  employeesLoading.value = true
  try {
    const { data } = await api.get('/employees/', { params: { search: query, limit: 50 } })
    employees.value = data
  } catch (e) {
    console.error('Ошибка поиска:', e)
  } finally {
    employeesLoading.value = false
  }
}

function openCreateDialog() {
  isEditing.value = false
  currentNoteId.value = null
  form.value = {
    month: filterMonth.value || (_now.getMonth() + 1),
    year: filterYear.value || _now.getFullYear(),
    department_id: filterDepartment.value || null,
    comment: '',
    entries: []
  }
  showNoteDialog.value = true
}

// 'ГГГГ-ММ-ДД' -> { month: 1..12, year }
function parsePeriodToMonthYear(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return { month: d.getMonth() + 1, year: d.getFullYear() }
}

function openEditDialog(note) {
  isEditing.value = true
  currentNoteId.value = note.id
  const { month, year } = parsePeriodToMonthYear(note.period_start)
  form.value = {
    month,
    year,
    department_id: note.department_id
      ? departments.value.find(d => d.id === note.department_id) || { id: note.department_id, name: note.department_name }
      : null,
    comment: note.comment || '',
    entries: note.entries.map(e => ({
      employee_id: e.employee_id,
      employee_name: e.employee_name,
      employee_tab_number: e.employee_tab_number,
      department_name: e.department_name,
      day_records: e.day_records.map(dr => ({
        day: dr.day,
        time_out: dr.time_out,
        time_in: dr.time_in,
        hours: dr.hours,
        reason: dr.reason || DEFAULT_REASON
      })),
      total_hours: e.total_hours || 0,
      work_hours: e.work_hours || 0,
      personal_hours: e.personal_hours || 0,
      undefined_hours: e.undefined_hours || 0
    }))
  }
  showNoteDialog.value = true
}

function openAddEmployeeDialog() {
  selectedEmployee.value = null
  employees.value = []
  showAddEmployeeDialog.value = true
}

function addEmployee() {
  if (!selectedEmployee.value) return

  const emp = selectedEmployee.value

  if (form.value.entries.some(e => e.employee_id === emp.id)) {
    alert('Этот сотрудник уже добавлен в записку')
    return
  }

  form.value.entries.push({
    employee_id: emp.id,
    employee_name: emp.full_name,
    employee_tab_number: emp.tab_number,
    department_name: emp.department_name || '',
    day_records: [],
    total_hours: 0,
    work_hours: 0,
    personal_hours: 0,
    undefined_hours: 0
  })

  selectedEmployee.value = null
  showAddEmployeeDialog.value = false
}

function removeEntry(idx) {
  if (!confirm('Удалить сотрудника из записки?')) return
  form.value.entries.splice(idx, 1)
}

function getDayRecord(entry, day) {
  return entry.day_records.find(dr => dr.day === day)
}

function openDayDialog(entry, day) {
  currentEntry.value = entry
  currentDay.value = day

  const existing = getDayRecord(entry, day)
  if (existing) {
    dayForm.value = {
      time_out: existing.time_out || '',
      time_in: existing.time_in || '',
      reason: existing.reason || DEFAULT_REASON,
      hours: existing.hours || 0
    }
  } else {
    dayForm.value = {
      time_out: '',
      time_in: '',
      reason: DEFAULT_REASON,
      hours: 0
    }
  }

  showDayDialog.value = true
}

// Поведение radio, но визуально чекбоксы: все три v-checkbox привязаны к одному
// dayForm.reason и имеют value="work"/"personal"/"undefined". Отметка одного чекбокса
// записывает его код в reason, поэтому галочка «переезжает» — активна ровно одна причина.
watch(() => dayForm.value.reason, (val) => {
  // Если пользователь случайно снял последнюю галочку (model стал null/'') —
  // возвращаем значение по умолчанию («Личная»), чтобы причина была всегда.
  if (val !== 'work' && val !== 'personal' && val !== 'undefined') {
    dayForm.value.reason = DEFAULT_REASON
  }
})

function calculateDayHours() {
  if (!dayForm.value.time_out || !dayForm.value.time_in) {
    dayForm.value.hours = 0
    return
  }

  const [hOut, mOut] = dayForm.value.time_out.split(':').map(Number)
  const [hIn, mIn] = dayForm.value.time_in.split(':').map(Number)

  let minutesOut = hOut * 60 + mOut
  let minutesIn = hIn * 60 + mIn

  if (minutesIn <= minutesOut) {
    minutesIn += 24 * 60  // переход через полночь
  }

  const diff = (minutesIn - minutesOut) / 60
  dayForm.value.hours = Math.round(diff * 100) / 100
}

// Следим за изменением времени — часы считаются автоматически
watch(() => [dayForm.value.time_out, dayForm.value.time_in], calculateDayHours)

function recalcEntryTotal(entry) {
  let work = 0
  let personal = 0
  let undef = 0

  for (const dr of entry.day_records) {
    const h = dr.hours || 0
    if (dr.reason === 'work') work += h
    else if (dr.reason === 'personal') personal += h
    else undef += h
  }

  entry.work_hours = Math.round(work * 100) / 100
  entry.personal_hours = Math.round(personal * 100) / 100
  entry.undefined_hours = Math.round(undef * 100) / 100
  const sum = entry.day_records.reduce((acc, dr) => acc + (dr.hours || 0), 0)
  entry.total_hours = Math.round(sum * 100) / 100
}

function saveDay() {
  const entry = currentEntry.value
  const day = currentDay.value
  if (!entry) return

  // Удаляем старую запись за этот день
  entry.day_records = entry.day_records.filter(dr => dr.day !== day)

  // Если есть время — добавляем новую запись с причиной
  if (dayForm.value.time_out || dayForm.value.time_in) {
    entry.day_records.push({
      day: day,
      time_out: dayForm.value.time_out || null,
      time_in: dayForm.value.time_in || null,
      hours: dayForm.value.hours || 0,
      reason: dayForm.value.reason || DEFAULT_REASON
    })
  }

  recalcEntryTotal(entry)

  showDayDialog.value = false
}

function clearDay() {
  dayForm.value = { time_out: '', time_in: '', reason: DEFAULT_REASON, hours: 0 }
  saveDay()
}

function getDayCellClass(entry, day) {
  const record = getDayRecord(entry, day)
  if (!record) return ''
  if (record.hours > 0) {
    // Разные цвета подсветки ячеек в зависимости от причины
    if (record.reason === 'work') return 'day-cell-work'
    if (record.reason === 'personal') return 'day-cell-personal'
    return 'day-cell-undefined'
  }
  return 'day-cell-partial'
}

async function saveNote() {
  const month = form.value.month || (_now.getMonth() + 1)
  const year = form.value.year || _now.getFullYear()
  const periodStart = monthStartStr(year, month)
  const periodEnd = monthEndStr(year, month)

  saving.value = true
  try {
    const payload = {
      period_start: periodStart,
      period_end: periodEnd,
      department_id: form.value.department_id?.id || null,
      comment: form.value.comment || null,
      entries: form.value.entries.map(e => ({
        employee_id: e.employee_id,
        day_records: e.day_records.map(dr => ({
          day: dr.day,
          time_out: dr.time_out || null,
          time_in: dr.time_in || null,
          reason: dr.reason || DEFAULT_REASON
        }))
      }))
    }

    if (isEditing.value) {
      await api.put(`/dismissal-notes/${currentNoteId.value}`, payload)
    } else {
      await api.post('/dismissal-notes/', payload)
    }

    showNoteDialog.value = false
    await loadNotes()
  } catch (e) {
    console.error('Ошибка сохранения:', e)
    alert('Ошибка: ' + (e.response?.data?.detail || 'неизвестная'))
  } finally {
    saving.value = false
  }
}

async function deleteNote(id) {
  if (!confirm('Удалить увольнительную записку?')) return
  try {
    await api.delete(`/dismissal-notes/${id}`)
    await loadNotes()
  } catch (e) {
    console.error('Ошибка удаления:', e)
    alert('Ошибка удаления: ' + (e.response?.data?.detail || 'неизвестная'))
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + (dateStr.length === 10 ? 'T00:00:00' : ''))
  return d.toLocaleDateString('ru-RU')
}

// Период записки для отображения в списке
function formatPeriod(startStr, endStr) {
  if (!startStr || !endStr) return ''
  if (startStr === endStr) return formatDate(startStr)
  return `${formatDate(startStr)} — ${formatDate(endStr)}`
}

onMounted(() => {
  loadNotes()
  loadDepartments()
})
</script>

<style scoped>
.dismissal-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
}

.dismissal-table th, .dismissal-table td {
  border: 1px solid #ddd;
  padding: 4px;
  vertical-align: middle;
}

.dismissal-table thead th {
  background-color: #2d5a3d;
  color: white;
  font-weight: bold;
  text-align: center;
  position: sticky;
  top: 0;
}

.col-num {
  width: 30px;
  text-align: center;
}

.col-fio {
  min-width: 180px;
  max-width: 220px;
  text-align: left;
  padding-left: 4px !important;
}

.col-dept {
  min-width: 120px;
  max-width: 150px;
  font-size: 11px;
  word-wrap: break-word;
}

.col-day {
  width: 50px;
  min-width: 50px;
  text-align: center;
  cursor: pointer;
  position: relative;
}

.col-day:hover {
  background-color: #e3f2fd !important;
}

.col-total {
  width: 70px;
  min-width: 70px;
  text-align: center;
  font-weight: bold;
  background-color: #f5f5f5;
}

/* Цветные колонки итогов по причинам */
.dismissal-table tbody .col-work {
  background-color: #e3f2fd !important;  /* светло-синий */
  color: #1565c0;
}

.dismissal-table tbody .col-personal {
  background-color: #fce4ec !important;  /* светло-розовый */
  color: #c2185b;
}

.dismissal-table tbody .col-undefined {
  background-color: #f5f5f5 !important;  /* светло-серый */
  color: #616161;
}

.dismissal-table tbody .col-grand-total {
  background-color: #e8f5e9 !important;  /* светло-зелёный */
  color: #2e7d32;
  font-weight: bold;
}

.reason-checkboxes {
  padding: 8px 0;
}

.col-actions {
  width: 50px;
  text-align: center;
}

.day-cell-filled {
  background-color: #e8f5e9 !important;
}

/* Подсветка ячеек дней по причине */
.day-cell-work {
  background-color: #e3f2fd !important;  /* синий — по работе */
}

.day-cell-personal {
  background-color: #fce4ec !important;  /* розовый — личная */
}

.day-cell-undefined {
  background-color: #eeeeee !important;  /* серый — неопределённо */
}

.day-cell-partial {
  background-color: #fff9c4 !important;
}

.day-time {
  font-size: 10px;
  line-height: 1.2;
  color: #1565c0;
}

.day-hours {
  font-size: 10px;
  font-weight: bold;
  color: #2e7d32;
  margin-top: 2px;
}
</style>
