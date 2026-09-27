<template>
  <div v-if="tabel">
    <div class="d-flex align-center mb-3 flex-wrap" style="gap: 8px;">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="'/tabels'" color="#2d5a3d">К табелям</v-btn>
      <h2 class="text-h5" style="font-weight:bold;">
        Табель: {{ monthNames[tabel.month - 1] }} {{ tabel.year }}
        <span v-if="tabel.department_name">— {{ tabel.department_name }}</span>
      </h2>
      <v-spacer />

      <v-btn variant="tonal" color="#2d5a3d" prepend-icon="mdi-book-outline" @click="codesDialog = true">
        Коды часов
      </v-btn>
      <v-btn color="green darken-1" prepend-icon="mdi-content-save" :loading="saving" @click="save(false)">
        Сохранить
      </v-btn>
    </div>

    <v-alert v-if="message" :type="messageType" closable density="compact" class="mb-3" @click:close="message=''">
      {{ message }}
    </v-alert>

    <div class="d-flex align-center flex-wrap mb-2" style="gap: 14px; font-size: 13px;">
      <span><span class="legend-box legend-weekend"></span> Выходной день</span>
      <span><span class="legend-box legend-holiday"></span> ★ Праздничный (нерабочий) день</span>
      <span v-if="calendarNotLoaded" class="text-caption text-grey-darken-1">
        Производственный календарь на {{ tabel.year }} год не загружен — показаны только выходные по пятидневке.
        Загрузите календарь на вкладке «Импорт».
      </span>
    </div>

    <div style="overflow-x:auto; border:1px solid #c8e6c9; border-radius:8px; background:white;">
      <table class="tabel-table" v-if="tabel.entries.length">
        <thead>
          <!-- ПЕРВЫЙ УРОВЕНЬ ШАПКИ -->
          <tr>
            <th class="col-no" rowspan="2">№<br>п/п</th>
            <th class="col-fio" rowspan="2">Ф.И.О.</th>
            <th class="col-days-header" :colspan="tabel.days_in_month">Дни недели</th>
            <th v-for="col in summaryColumns" :key="col.key" class="col-summary-header" rowspan="2"
                :title="col.label">
              {{ col.label }}
            </th>
            <th class="col-del" rowspan="2"></th>
          </tr>
          <!-- ВТОРОЙ УРОВЕНЬ ШАПКИ: дни недели + числа -->
          <tr>
            <th v-for="d in tabel.days_in_month" :key="d" class="col-day-header"
                :class="{ 'day-weekend-header': isWeekend(d), 'day-holiday-header': isHoliday(d) }"
                :title="holidayName(d)">
              <div class="day-name">{{ getDayOfWeek(d) }}</div>
              <div class="day-number">{{ d }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in tabel.entries" :key="row.employee_id">
            <td class="col-no">{{ idx + 1 }}</td>
            <td class="col-fio" :title="row.full_name">
              {{ row.full_name }}<br /><small class="text-grey">{{ row.tab_number }}</small>
            </td>
            <td v-for="d in tabel.days_in_month" :key="d" class="cell-day"
                :class="{ 'cell-weekend': isWeekend(d), 'cell-holiday': isHoliday(d) }">
              <div class="cell-wrap" :class="{ 'is-open': openCell === row.employee_id + '_' + d }">
                <input
                  class="cell-input"
                  :class="{ 'is-code': isCodeText(row.days[d]), 'is-error-cell': hasError(row.employee_id, d) }"
                  :value="row.days[d] || ''"
                  readonly
                  tabindex="-1"
                  @click="openCellPicker(row.employee_id, d, $event)"
                />
                <v-menu
                  :model-value="openCell === row.employee_id + '_' + d"
                  :positioned="true"
                  :style="{ left: menuX + 'px', top: menuY + 'px' }"
                  :scrim="false"
                  :hide-scroll="false"
                  :min-width="260"
                  content-class="cell-menu"
                  max-height="320"
                  @update:model-value="(v) => { if (!v) openCell = null }"
                >
                  <div style="width: 300px;">
                    <v-text-field
                      ref="cellSearchRef"
                      v-model="cellQuery"
                      density="compact"
                      variant="solo-filled"
                      flat-end
                      hide-details
                      clearable
                      placeholder="Поиск (напр. 8)"
                      prepend-inner-icon="mdi-magnify"
                      autofocus
                      class="pa-1"
                    />
                    <v-list density="compact" max-height="260" class="overflow-y-auto">
                      <v-list-item
                        v-for="it in filteredCellItems"
                        :key="it.value"
                        :title="it.title"
                        prepend-icon="mdi-check"
                        @click="pickCellValue(row.employee_id, d, it.value)"
                      />
                      <v-list-item v-if="!filteredCellItems.length" title="Ничего не найдено" disabled />
                    </v-list>
                  </div>
                </v-menu>
              </div>
            </td>
            <!-- ЗНАЧЕНИЯ ИТОГОВЫХ КОЛОНОК -->
            <td v-for="col in summaryColumns" :key="col.key" class="col-summary-cell text-center">
              {{ calculateSummary(row)[col.key] || 0 }}
            </td>
            <td class="col-del">
              <span class="code-chips" v-if="codesForRow(row).length">
                <v-chip v-for="c in codesForRow(row)" :key="c.code" size="x-small"
                        variant="tonal" color="#2d5a3d" style="margin:1px;">{{ c.code }}</v-chip>
              </span>
              <a href="#" class="text-red text-caption" style="white-space:nowrap;"
                 @click.prevent="removeEmployee(row)">Удалить</a>
            </td>
          </tr>

          <tr class="add-row">
            <td></td>
            <td class="add-cell">
              <div class="d-flex align-center" style="gap: 6px;">
                <v-autocomplete
                  v-model="selectedEmployee"
                  :items="employeeOptions"
                  item-title="label"
                  item-value="id"
                  :menu-icon="null"
                  label="Добавить сотрудника (поиск по фамилии)"
                  prepend-inner-icon="mdi-magnify"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                  auto-select-first
                  style="min-width: 320px; max-width: 420px;"
                  @update:model-value="onEmployeePicked"
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props" :title="item.raw.label"
                                 :subtitle="item.raw.tab_number ? 'Таб. ' + item.raw.tab_number : ''" />
                  </template>
                </v-autocomplete>
                <span v-if="selectedEmployee" class="text-caption text-grey">— строка появится здесь</span>
              </div>
            </td>
            <td :colspan="tabel.days_in_month + summaryColumns.length + 1"></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="pa-4">
        <div class="d-flex align-center mb-4" style="gap: 6px;">
          <v-autocomplete
            v-model="selectedEmployee"
            :items="employeeOptions"
            item-title="label"
            item-value="id"
            :menu-icon="null"
            label="Добавить сотрудника (поиск по фамилии)"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="outlined"
            clearable
            hide-details
            auto-select-first
            style="min-width: 320px; max-width: 420px;"
            @update:model-value="onEmployeePicked"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props" :title="item.raw.label"
                           :subtitle="item.raw.tab_number ? 'Таб. ' + item.raw.tab_number : ''" />
            </template>
          </v-autocomplete>
          <span class="text-caption text-grey">— первый сотрудник появится здесь</span>
        </div>
      </div>
    </div>

    <!-- Справочник «Коды часов» -->
    <v-dialog v-model="codesDialog" max-width="900">
      <v-card title="Справочник «Коды часов»">
        <v-card-text>
          <v-table density="compact">
            <thead>
              <tr>
                <th>Код</th>
                <th>Наименование</th>
                <th>Часов день</th>
                <th>Часов ночь</th>
                <th style="min-width: 200px;">Направления</th>
                <th v-if="auth.isAdmin"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in timeCodes" :key="c.id">
                <td><b>{{ c.code }}</b></td>
                <td>{{ c.name }}</td>
                <td>{{ c.hours_day }}</td>
                <td>{{ c.hours_night }}</td>
                <td>
                  <v-chip v-for="dest in (c.destinations || [])" :key="dest" size="x-small" class="mr-1 mb-1">
                    {{ summaryColumns.find(col => col.key === dest)?.label || dest }}
                  </v-chip>
                  <span v-if="!c.destinations || c.destinations.length === 0" class="text-grey text-caption">Не указано</span>
                </td>
                <td v-if="auth.isAdmin">
                  <v-btn size="x-small" icon="mdi-delete" color="red" variant="text" @click="deleteCode(c)" />
                </td>
              </tr>
            </tbody>
          </v-table>
          
          <template v-if="auth.isAdmin">
            <v-form @submit.prevent="addCode" class="d-flex flex-wrap mt-4" style="gap:8px; align-items: flex-start;">
              <v-text-field v-model="newCode.code" label="Код" density="compact" variant="outlined" style="max-width:100px;" hide-details />
              <v-text-field v-model="newCode.name" label="Наименование" density="compact" variant="outlined" style="flex:1; min-width: 150px;" hide-details />
              <v-text-field v-model.number="newCode.hours_day" label="День" type="number" step="0.01" density="compact" variant="outlined" style="max-width:80px;" hide-details />
              <v-text-field v-model.number="newCode.hours_night" label="Ночь" type="number" step="0.01" density="compact" variant="outlined" style="max-width:80px;" hide-details />
              
              <v-select
                v-model="newCode.destinations"
                :items="summaryColumns.map(c => ({ title: c.label, value: c.key }))"
                label="Куда попадет"
                density="compact"
                variant="outlined"
                multiple
                chips
                closable-chips
                style="min-width: 250px; flex: 2;"
                hide-details
              />
              
              <v-btn color="#2d5a3d" type="submit" prepend-icon="mdi-plus" class="align-self-end" style="height: 40px;">Добавить</v-btn>
            </v-form>
            <div v-if="codeError" class="text-red mt-2">{{ codeError }}</div>
          </template>
          <div v-else class="text-caption text-grey mt-2">
            Изменять справочник может только Администратор.
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="codesDialog = false">Закрыть</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
  <v-progress-circular v-else indeterminate color="#2d5a3d" />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { auth } from '../auth'

const route = useRoute()
const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
const dayOfWeekNames = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

const tabel = ref(null)
const timeCodes = ref([])
const dirty = ref({})
const cellErrors = ref({})
const message = ref('')
const messageType = ref('success')
const saving = ref(false)

const codesDialog = ref(false)
const newCode = ref({ code: '', name: '', hours_day: 0, hours_night: 0, destinations: [] })
const codeError = ref('')

// Итоговые колонки — полные названия для вертикальных заголовков
const summaryColumns = [
  { key: 'fact_days', label: 'фактической работы' },
  { key: 'total_hours', label: 'Итого часов' },
  { key: 'vacation', label: 'трудовой отпуск' },
  { key: 'sick', label: 'болезнь' },
  { key: 'admin_leave', label: 'с разрешения администрации' },
  { key: 'weekend_holiday', label: 'выходные и праздн.' },
  { key: 'other_absence', label: 'Другие неявки' },
  { key: 'overtime_days', label: 'сверхурочные дни' },
  { key: 'overtime_hours', label: 'Сверхурочные часы' },
  { key: 'night_hours', label: 'ночные часы' },
  { key: 'tariff_hours', label: 'Итого часов по участку' },
  { key: 'kdu_work_days', label: 'КДУ УШН' },
  { key: 'kdu_weekend_days', label: 'КДУ, вых. дни УШН' }
]

// Получить день недели для числа месяца
function getDayOfWeek(day) {
  if (!tabel.value) return ''
  const date = new Date(tabel.value.year, tabel.value.month - 1, day)
  return dayOfWeekNames[date.getDay()]
}

const weekendSet = computed(() => new Set(tabel.value?.weekend_days || []))
const holidaySet = computed(() => new Set(tabel.value?.holiday_days || []))
function isWeekend(d) { return weekendSet.value.has(d) }
function isHoliday(d) { return holidaySet.value.has(d) }
function holidayName(d) {
  const n = tabel.value?.holiday_names?.[d]
  return n ? `${d}: ${n} — праздничный (нерабочий) день` : ''
}
const calendarNotLoaded = computed(() =>
  !!tabel.value && (tabel.value.holiday_days?.length ?? 0) === 0)

const allEmployees = ref([])
const selectedEmployee = ref(null)
let addingInProgress = false

const employeeOptions = computed(() =>
  allEmployees.value.map(e => ({
    ...e,
    label: `${e.full_name}${e.department_name ? ' — ' + e.department_name : ''}`
  }))
)

async function loadEmployees() {
  const { data } = await api.get('/tabels/search/employees', { params: { q: '' } })
  const inTabel = new Set((tabel.value?.entries || []).map(r => r.employee_id))
  allEmployees.value = data.filter(e => !inTabel.has(e.id))
}

async function onEmployeePicked(empId) {
  if (!empId || addingInProgress) return
  addingInProgress = true
  try {
    await api.post(`/tabels/${route.params.id}/employees`, { employee_ids: [empId] })
    await loadTabel()
    await loadEmployees()
  } catch (e) {
    message.value = e.response?.data?.detail || 'Ошибка добавления'
    messageType.value = 'error'
  } finally {
    selectedEmployee.value = null
    addingInProgress = false
  }
}

function codeSet() {
  return new Set(timeCodes.value.map(c => c.code.toLowerCase()))
}
function isCodeText(v) {
  return !!v && codeSet().has(String(v).trim().toLowerCase())
}

function hoursToHM(h) {
  const total = Math.round((Number(h) || 0) * 60)
  if (!total) return '0м'
  const hh = Math.floor(total / 60)
  const mm = total % 60
  if (hh && mm) return `${hh}ч${mm}м`
  if (hh) return `${hh}ч`
  return `${mm}м`
}

const cellItems = computed(() => {
  return timeCodes.value.map(c => {
    const h = (Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)
    const hrs = h ? ` (${hoursToHM(h)})` : ''
    return {
      title: `${c.code} — ${c.name}${hrs}`,
      value: c.code,
    }
  })
})

function cellFilter(value, query) {
  if (!query) return true
  const q = String(query).toLowerCase().replace(',', '.')
  const v = String(value ?? '').toLowerCase().replace(',', '.')
  return v.startsWith(q) || v.includes(q)
}

const openCell = ref(null)
const cellQuery = ref('')
const menuX = ref(0)
const menuY = ref(0)

const filteredCellItems = computed(() => {
  const q = cellQuery.value.trim().toLowerCase().replace(',', '.')
  if (!q) return cellItems.value
  return cellItems.value.filter(it => cellFilter(it.value, q))
})

function openCellPicker(empId, day, event) {
  const key = empId + '_' + day
  if (openCell.value === key) { openCell.value = null; return }
  menuX.value = event?.clientX ?? 0
  menuY.value = (event?.clientY ?? 0) + 24
  openCell.value = key
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  cellQuery.value = row?.days[day] || ''
}

function pickCellValue(empId, day, val) {
  const text = String(val ?? '').trim()
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  if (row) row.days[day] = text
  markDirty(empId, day)
  validateCell(empId, day)
  openCell.value = null
  cellQuery.value = ''
}

function isValidValue(v) {
  if (!v || !v.trim()) return true
  const s = v.trim().replace(',', '.')
  if (codeSet().has(s.toLowerCase())) return true
  if (/^\d{1,2}(\.\d{1,2})?$/.test(s)) {
    const n = parseFloat(s)
    return n > 0 && n <= 23.59
  }
  return false
}

function hasError(empId, day) {
  return !!cellErrors.value[`${empId}_${day}`]
}

function validateCell(empId, day) {
  const key = `${empId}_${day}`
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  if (row && !isValidValue(row.days[day])) cellErrors.value[key] = true
  else delete cellErrors.value[key]
}

function markDirty(empId, day) {
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  dirty.value[`${empId}_${day}`] = row ? row.days[day] : ''
}

function cellMinutes(v) {
  const s = String(v ?? '').trim().toLowerCase().replace(/,/g, '.')
  if (!s) return 0
  let m = s.match(/^(\d+)\s*ч\s*(\d+)?\s*м?$/)
  if (m) return parseInt(m[1]) * 60 + (m[2] ? parseInt(m[2]) : 0)
  m = s.match(/^(\d+)\s*м$/)
  if (m) return parseInt(m[1])
  m = s.match(/^(\d+):([0-5]\d)$/)
  if (m) return parseInt(m[1]) * 60 + parseInt(m[2])
  if (/^\d+(\.\d+)?$/.test(s)) return Math.round(parseFloat(s) * 60)
  const c = timeCodes.value.find(x => x.code.toLowerCase() === s)
  if (c) return Math.round(((Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)) * 60)
  return 0
}

function totalHours(row) {
  let minutes = 0
  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    minutes += cellMinutes(row.days[d])
  }
  const hh = Math.floor(minutes / 60)
  const mm = minutes % 60
  return mm ? `${hh}ч${mm}м` : `${hh}ч`
}

function calculateSummary(row) {
  const summary = {}
  summaryColumns.forEach(col => summary[col.key] = 0)

  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    const val = String(row.days[d] || '').trim()
    if (!val) continue

    if (/^\d{1,2}([.,]\d{1,2})?$/.test(val)) {
      const num = parseFloat(val.replace(',', '.'))
      summary.total_hours += num
      summary.fact_days += 1
      summary.tariff_hours += num
      continue
    }

    const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === val.toLowerCase())
    if (codeObj) {
      const hours = (Number(codeObj.hours_day) || 0) + (Number(codeObj.hours_night) || 0)
      const dests = codeObj.destinations || []

      dests.forEach(dest => {
        if (summary.hasOwnProperty(dest)) {
          const isDays = dest.includes('day') || dest.includes('дни') || dest.includes('days')
          summary[dest] += isDays ? 1 : hours
        }
      })
    }
  }

  for (const key in summary) {
    if (key.includes('hours') || key.includes('час')) {
      summary[key] = Math.round(summary[key] * 100) / 100
    }
    if (key.includes('day') || key.includes('дни') || key.includes('days')) {
      summary[key] = Math.round(summary[key])
    }
  }

  return summary
}

async function loadTabel() {
  const raw = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const id = Number(raw)
  if (!Number.isInteger(id) || id <= 0) {
    console.error('Некорректный id табеля в URL:', raw)
    message.value = 'Некорректный адрес табеля'
    messageType.value = 'error'
    return
  }
  try {
    const { data } = await api.get(`/tabels/${id}`)
    tabel.value = data
    dirty.value = {}
    cellErrors.value = {}
  } catch (e) {
    const status = e.response?.status
    const detail = typeof e.response?.data?.detail === 'string'
      ? e.response.data.detail
      : (status ? `Ошибка сервера ${status} при загрузке табеля` : 'Сеть недоступна')
    message.value = detail
    messageType.value = 'error'
    if (status === 401 && auth.isAuthenticated?.()) {
      auth.logout?.()
      window.location.href = '/login'
    }
  }
}

async function removeEmployee(row) {
  if (!confirm(`Убрать ${row.full_name} из табеля?`)) return
  await api.delete(`/tabels/${route.params.id}/entries/${row.employee_id}`)
  await loadTabel()
  await loadEmployees()
}

async function save(showMsg = true) {
  const updates = Object.entries(dirty.value).map(([key, value]) => {
    const [empId, day] = key.split('_')
    return { employee_id: Number(empId), day: Number(day), value }
  })
  if (!updates.length) return true
  if (Object.keys(cellErrors.value).length) {
    message.value = 'Есть некорректные ячейки — исправьте их перед сохранением'
    messageType.value = 'error'
    return false
  }
  saving.value = true
  try {
    await api.put(`/tabels/${route.params.id}/cells`, updates)
    dirty.value = {}
    if (showMsg) {
      message.value = 'Сохранено'
      messageType.value = 'success'
      setTimeout(() => { if (message.value === 'Сохранено') message.value = '' }, 2000)
    }
    return true
  } catch (e) {
    message.value = e.response?.data?.detail || 'Ошибка сохранения'
    messageType.value = 'error'
    return false
  } finally {
    saving.value = false
  }
}

function codesForRow(row) {
  const used = new Set()
  Object.values(row.days || {}).forEach(v => {
    const t = String(v || '').trim().toLowerCase()
    if (!t) return
    const c = timeCodes.value.find(x => x.code.toLowerCase() === t)
    if (c) used.add(c.code)
  })
  return Array.from(used).map(code => timeCodes.value.find(x => x.code === code))
}

async function loadCodes() {
  try {
    const { data } = await api.get('/time-codes/')
    timeCodes.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('Не удалось загрузить справочник кодов часов', e)
  }
}

async function addCode() {
  codeError.value = ''
  try {
    await api.post('/time-codes/', newCode.value)
    newCode.value = { code: '', name: '', hours_day: 0, hours_night: 0, destinations: [] }
    await loadCodes()
  } catch (e) {
    codeError.value = typeof e.response?.data?.detail === 'string'
      ? e.response.data.detail : 'Ошибка добавления кода'
  }
}

async function deleteCode(c) {
  if (!confirm(`Удалить код «${c.code}»?`)) return
  await api.delete(`/time-codes/${c.id}`)
  await loadCodes()
}

setInterval(() => { if (Object.keys(dirty.value).length) save(false) }, 30000)

onMounted(async () => {
  await Promise.all([loadTabel(), loadCodes()])
  await loadEmployees()
})
</script>

<style scoped>
.tabel-table {
  border-collapse: collapse;
  font-size: 12px;
  white-space: nowrap;
}
.tabel-table th, .tabel-table td {
  border: 1px solid #000;
  padding: 2px;
}

/* Шапка таблицы */
.tabel-table thead th {
  background-color: white !important;
  color: black !important;
  font-weight: bold;
  text-align: center;
  vertical-align: middle;
}

.col-no { 
  width: 40px; 
  text-align: center;
  font-size: 11px;
}

.col-fio { 
  min-width: 200px; 
  text-align: left; 
  padding-left: 6px !important;
}

/* Заголовок "Дни недели" */
.col-days-header {
  font-size: 13px;
  font-weight: bold;
  padding: 4px !important;
}

/* Ячейки дней в шапке */
.col-day-header {
  width: 38px;
  min-width: 38px;
  max-width: 38px;
  padding: 2px 1px !important;
  font-size: 10px;
}

.day-name {
  font-size: 9px;
  font-weight: normal;
  color: #666;
}

.day-number {
  font-size: 11px;
  font-weight: bold;
}

/* Выходные и праздники в шапке */
.day-weekend-header {
  background-color: #f0f0f0 !important;
}

.day-holiday-header {
  background-color: #fff3cd !important;
}

/* Итоговые колонки — вертикальные заголовки */
.col-summary-header {
  width: 28px;
  min-width: 28px;
  max-width: 28px;
  padding: 8px 2px !important;
  font-size: 10px;
  font-weight: bold;
  text-align: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  transform: rotate(180deg);
  white-space: nowrap;
  vertical-align: middle;
  background-color: white !important;
  border-left: 1px solid #000 !important;
}

/* Ячейки итоговых значений */
.col-summary-cell {
  width: 28px;
  min-width: 28px;
  max-width: 28px;
  padding: 2px 1px !important;
  font-size: 11px;
  font-weight: normal;
  text-align: center;
  background-color: white !important;
  border-left: 1px solid #000 !important;
}

.col-del { 
  width: 40px;
  background-color: white !important;
}

/* Ячейки дней */
.cell-day {
  width: 38px;
  min-width: 38px;
  max-width: 38px;
  padding: 2px !important;
}

.cell-weekend { 
  background-color: #f0f0f0; 
}

.cell-holiday { 
  background-color: #fff3cd; 
}

.holiday-mark { 
  font-size: 10px; 
  margin-left: 1px; 
  vertical-align: top; 
}

.legend-box { 
  display: inline-block; 
  width: 14px; 
  height: 14px; 
  border-radius: 3px;
  border: 1px solid #c8e6c9; 
  vertical-align: middle; 
  margin-right: 4px; 
}

.legend-weekend { 
  background-color: #f0f0f0; 
}

.legend-holiday { 
  background-color: #fff3cd; 
}

/* Ячейка табеля */
.cell-wrap { 
  position: relative; 
  width: 100%; 
  height: 24px; 
}

.cell-input {
  width: 100%;
  height: 24px;
  box-sizing: border-box;
  border: none;
  outline: none;
  background: transparent;
  text-align: center;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.87);
}

.cell-input:hover { 
  background: #e8f5e9; 
}

.cell-wrap.is-open .cell-input { 
  background: #e8f5e9; 
  box-shadow: inset 0 0 0 2px #2d5a3d; 
}

.is-code { 
  color: #1565c0; 
  font-weight: bold; 
}

.is-error, .is-error-cell { 
  background: #ffebee !important; 
  outline: 2px solid red; 
}

.add-row td { 
  border-top: 2px dashed #a5d6a7; 
  background: #f9fbe7; 
}

.add-cell { 
  padding: 6px 8px !important; 
}
</style>

<style>
.cell-menu .v-overlay__content { 
  background: white; 
  border-radius: 8px; 
}
</style>