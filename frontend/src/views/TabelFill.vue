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
                <v-tooltip location="bottom" :max-width="220" :disabled="!row.days[d]">
                  <template #activator="{ props: tooltipProps }">
                    <input
                      class="cell-input cell-tip-area"
                      :class="{ 'is-code': isCodeText(row.days[d]), 'is-error-cell': hasError(row.employee_id, d), 'is-overtime-cell': isOvertimeCell(row, row.days[d], d) }"
                      :value="row.days[d] || ''"
                      readonly
                      tabindex="-1"
                      v-bind="tooltipProps"
                      @click="openCellPicker(row.employee_id, d, $event)"
                    />
                  </template>
                  <!-- Подсказка с деталями ячейки: код из справочника / числовые часы -->
                  <div v-if="cellTipData(row.days[d], row, d)" class="day-tooltip">
                    <div class="font-weight-bold mb-1">{{ tooltipDateLabel(d) }}</div>
                    <template v-if="cellTipData(row.days[d], row, d).kind === 'code'">
                      <div><v-icon size="x-small" icon="mdi-tag-text-outline" class="mr-1" />Код: {{ cellTipData(row.days[d], row, d).code }}</div>
                      <div><v-icon size="x-small" icon="mdi-information-outline" class="mr-1" />{{ cellTipData(row.days[d], row, d).name }}</div>
                      <v-divider class="tooltip-divider my-1"></v-divider>
                      <div><v-icon size="x-small" icon="mdi-weather-sunny" class="mr-1" />День: {{ fmtNum(cellTipData(row.days[d], row, d).day) }}</div>
                      <div><v-icon size="x-small" icon="mdi-weather-night" class="mr-1" />Ночь: {{ fmtNum(cellTipData(row.days[d], row, d).night) }}</div>
                      <div class="font-weight-bold"><v-icon size="x-small" icon="mdi-check-circle-outline" class="mr-1" />Итого часов: {{ fmtNum(cellTipData(row.days[d], row, d).total) }}</div>
                      <div v-if="cellTipData(row.days[d], row, d).ot > 0" class="text-warning">
                        <v-icon size="x-small" icon="mdi-alert-outline" class="mr-1" />Сверхурочно: {{ fmtNum(cellTipData(row.days[d], row, d).ot) }} (норма по графику {{ fmtNum(getDayNorm(row, d)) }})
                      </div>
                    </template>
                    <template v-else>
                      <div><v-icon size="x-small" icon="mdi-clock-outline" class="mr-1" />Введено: {{ fmtNum(cellTipData(row.days[d], row, d).hours) }} ч.</div>
                      <div><v-icon size="x-small" icon="mdi-target" class="mr-1" />Норма по графику: {{ fmtNum(cellTipData(row.days[d], row, d).norm) }} ч.</div>
                      <v-divider class="tooltip-divider my-1"></v-divider>
                      <div><v-icon size="x-small" icon="mdi-briefclockcase-outline" class="mr-1" />Обычные: {{ fmtNum(cellTipData(row.days[d], row, d).regular) }} ч.</div>
                      <div v-if="cellTipData(row.days[d], row, d).ot > 0" class="text-warning font-weight-bold">
                        <v-icon size="x-small" icon="mdi-alert-outline" class="mr-1" />Сверхурочные: {{ fmtNum(cellTipData(row.days[d], row, d).ot) }} ч.
                      </div>
                    </template>
                  </div>
                  <!-- Пустая ячейка: tooltip отключён (:disabled), текст доступен через cellTipText -->
                  <div v-else class="day-tooltip">
                    <div class="font-weight-bold mb-1">{{ tooltipDateLabel(d) }}</div>
                    <div class="text-caption">{{ cellTipText(null) }}</div>
                  </div>
                </v-tooltip>
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
              <!-- Ручные колонки КДУ: редактируемый input (0..5, шаг 0.01) -->
              <input
                v-if="col.unit === 'manual'"
                type="number"
                class="kdu-input"
                min="0" max="5" step="0.01"
                :value="row[col.key] ?? ''"
                @input="onKduInput(row, col.key, $event)"
                @blur="onKduBlur(row, col.key)"
                @click.stop
              />
              <template v-else>{{ calculateSummary(row)[col.key] || 0 }}</template>
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
                  label="Добавить сотрудника (поиск по ФИО, таб. номеру, подразделению)"
                  prepend-inner-icon="mdi-magnify"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                  auto-select-first
                  no-filter
                  :filter="filterEmployees"
                  no-data-text="Ничего не найдено"
                  style="min-width: 320px; max-width: 420px;"
                  @update:model-value="onEmployeePicked"
                  @update:search="onEmpSearch"
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
            label="Добавить сотрудника (поиск по ФИО, таб. номеру, подразделению)"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="outlined"
            clearable
            hide-details
            auto-select-first
            no-filter
            :filter="filterEmployees"
            no-data-text="Ничего не найдено"
            style="min-width: 320px; max-width: 420px;"
            @update:model-value="onEmployeePicked"
            @update:search="onEmpSearch"
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
          <v-table density="compact" hover>
            <thead>
              <tr>
                <th style="width: 80px;">Код</th>
                <th>Наименование</th>
                <th style="width: 90px;">Часов день</th>
                <th style="width: 90px;">Часов ночь</th>
                <th style="min-width: 250px; max-width: 400px;">Направления</th>
                <th v-if="auth.isAdmin" style="width: 100px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in timeCodes" :key="c.id" class="code-row">
                <td><b>{{ c.code }}</b></td>
                <td>{{ c.name }}</td>
                <td class="text-center">{{ c.hours_day }}</td>
                <td class="text-center">{{ c.hours_night }}</td>
                
                <td style="white-space: normal !important; vertical-align: middle;">
                  <div class="d-flex flex-wrap" style="gap: 4px;">
                    <v-chip v-for="dest in (c.destinations || [])" :key="dest" size="x-small" variant="tonal" color="#2d5a3d">
                      {{ summaryColumns.find(col => col.key === dest)?.label || dest }}
                    </v-chip>
                    <span v-if="!c.destinations || c.destinations.length === 0" class="text-grey text-caption">Не указано</span>
                  </div>
                </td>
                
                <td v-if="auth.isAdmin" class="text-center">
                  <v-btn size="x-small" icon="mdi-pencil" color="blue" variant="text" @click="editCode(c)" class="mr-1" />
                  <v-btn size="x-small" icon="mdi-delete" color="red" variant="text" @click="deleteCode(c)" />
                </td>
              </tr>
            </tbody>
          </v-table>
          
          <template v-if="auth.isAdmin">
            <v-divider class="my-4" />
            <div class="text-h6 mb-3">
              {{ isEditing ? 'Редактирование кода' : 'Добавление нового кода' }}
              <span v-if="isEditing" class="text-caption text-grey ml-2">({{ editingCode?.code }})</span>
            </div>
            
            <v-form @submit.prevent="saveCode" class="d-flex flex-wrap" style="gap:8px; align-items: flex-start;">
              <v-text-field 
                v-model="newCode.code" 
                :label="isEditing ? 'Код (нельзя изменить)' : 'Код'" 
                :readonly="isEditing"
                density="compact" 
                variant="outlined" 
                style="max-width:100px;" 
                hide-details 
              />
              <v-text-field 
                v-model="newCode.name" 
                label="Наименование" 
                density="compact" 
                variant="outlined" 
                style="flex:1; min-width: 150px;" 
                hide-details 
              />
              <v-text-field 
                v-model.number="newCode.hours_day" 
                label="День" 
                type="number" 
                step="0.01" 
                density="compact" 
                variant="outlined" 
                style="max-width:80px;" 
                hide-details 
              />
              <v-text-field 
                v-model.number="newCode.hours_night" 
                label="Ночь" 
                type="number" 
                step="0.01" 
                density="compact" 
                variant="outlined" 
                style="max-width:80px;" 
                hide-details 
              />
              
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
              
              <v-btn color="#2d5a3d" type="submit" prepend-icon="mdi-content-save" class="align-self-end" style="height: 40px;">
                {{ isEditing ? 'Сохранить' : 'Добавить' }}
              </v-btn>
              
              <v-btn v-if="isEditing" variant="outlined" color="grey" @click="cancelEdit" class="align-self-end" style="height: 40px;">
                Отмена
              </v-btn>
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
const dirtyKdu = ref({})   // изменённые ручные значения КДУ: key = `${employee_id}_${field}`
const cellErrors = ref({})
const message = ref('')
const messageType = ref('success')
const saving = ref(false)

const codesDialog = ref(false)
const newCode = ref({ code: '', name: '', hours_day: 0, hours_night: 0, destinations: [] })
const codeError = ref('')
const isEditing = ref(false)
const editingCode = ref(null)

// ИСПРАВЛЕНО: Добавлено свойство unit ('days' или 'hours') для точного расчета
const summaryColumns = ref([
  { key: 'fact_days', label: 'фактической работы', unit: 'days' },
  { key: 'total_hours', label: 'Итого часов', unit: 'hours' },
  { key: 'vacation', label: 'трудовой отпуск', unit: 'days' },
  { key: 'sick', label: 'болезнь', unit: 'days' },
  { key: 'admin_leave', label: 'с разрешения администрации', unit: 'days' },
  { key: 'weekend_holiday', label: 'выходные и праздн.', unit: 'days' },
  { key: 'other_absence', label: 'Другие неявки', unit: 'days' },
  { key: 'overtime_days', label: 'сверхурочные дни', unit: 'days' },
  { key: 'overtime_hours', label: 'Сверхурочные часы', unit: 'hours' },
  { key: 'night_hours', label: 'ночные часы', unit: 'hours' },
  { key: 'tariff_hours', label: 'Итого часов по участку', unit: 'hours' },
  { key: 'kdu_work_days', label: 'КДУ', unit: 'manual' },
  { key: 'kdu_weekend_days', label: 'КДУ вых. дня', unit: 'manual' }
])

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
let empSearchTimer = null

// Нормализация для поиска: нижний регистр + Ё->Е
const normSearch = s => String(s ?? '').toLowerCase().replace(/ё/g, 'е')

// Поиск по подстроке по всем полям: ФИО, табельный номер, подразделение.
// Регистронезависимо: «роман» находит и «Романов», и «Бельков Роман».
function empMatches(e, term) {
  const t = normSearch(term)
  return (
    normSearch(e.full_name).includes(t) ||
    normSearch(e.tab_number).includes(t) ||
    normSearch(e.department_name).includes(t)
  )
}

// Фильтрация внутри v-autocomplete (не через startsWith по умолчанию)
function filterEmployees(items, query) {
  if (!query || !query.trim()) return items.slice(0, 50)
  return items.filter(e => empMatches(e.raw ?? e, query)).slice(0, 50)
}

const employeeOptions = computed(() =>
  allEmployees.value.map(e => ({
    ...e,
    label: `${e.full_name}${e.tab_number ? ' — Таб. ' + e.tab_number : ''}${e.department_name ? ' — ' + e.department_name : ''}`
  }))
)

async function loadEmployees(q = '') {
  const { data } = await api.get('/tabels/search/employees', { params: { q } })
  const inTabel = new Set((tabel.value?.entries || []).map(r => r.employee_id))
  allEmployees.value = data.filter(e => !inTabel.has(e.id))
}

// Серверный поиск с debounce 300мс (минимум 1 символ)
function onEmpSearch(q) {
  clearTimeout(empSearchTimer)
  if (!q || q.trim().length < 1) return
  empSearchTimer = setTimeout(async () => {
    try { await loadEmployees(q.trim()) } catch (e) { /* ignore */ }
  }, 300)
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

// ===== Tooltip для ячеек табеля =====
const MONTH_NAMES_RU_GENITIVE = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
const DAY_NAMES_RU_FULL = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

// Дата в tooltip: «Понедельник, 28 сентября 2026»
function tooltipDateLabel(day) {
  const t = tabel.value
  if (!t) return ''
  const date = new Date(t.year, t.month - 1, day)
  return `${DAY_NAMES_RU_FULL[date.getDay()]}, ${day} ${MONTH_NAMES_RU_GENITIVE[t.month - 1]} ${t.year}`
}

// Число без хвостовых нулей: 8.50 → «8.5», 8 → «8»
function fmtNum(n) {
  const v = Number(n) || 0
  return String(Number(v.toFixed(2)))
}

// Разбор числового значения ячейки («8.5», «8ч15м», «8:15») в часы
function rawToHours(s) {
  const str = String(s ?? '').trim().replace(',', '.')
  let m = str.match(/^(\d+(?:\.\d+)?)\s*ч\s*(\d+)?\s*м?$/)
  if (m) return Number(m[1]) + (Number(m[2] || 0) / 60)
  m = str.match(/^(\d+)\s*:\s*(\d+)$/)
  if (m) return Number(m[1]) + Number(m[2]) / 60
  m = str.match(/^(\d+(?:\.\d+)?)$/)
  if (m) return Number(m[1])
  return null
}

// Данные для содержимого tooltip: код из справочника или числовое значение.
// Для числовых значений дополнительно показываем разбивку по норме (norm_hours):
// введено / норма / сверхурочные.
// Норма часов для конкретного дня месяца: из графика работы по дню недели.
// Если графика нет — fallback: employees.norm_hours, иначе 8.
function getDayNorm(row, d) {
  const dn = row && row.day_norms ? row.day_norms[d] : undefined
  if (dn !== undefined && dn !== null) return Number(dn) || 0
  return normOf(row)
}

function cellTipData(val, row, d) {
  if (!val) return null
  const s = String(val).trim()
  const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === s.toLowerCase())
  if (codeObj) {
    const day = Number(codeObj.hours_day) || 0
    const night = Number(codeObj.hours_night) || 0
    const total = day + night
    let ot = 0
    if (row && total > 0 && !(codeObj.destinations || []).includes('overtime_hours')) {
      ot = Math.max(0, total - getDayNorm(row, d))
    }
    return { kind: 'code', code: codeObj.code, name: codeObj.name, day, night, total, ot }
  }
  const hours = rawToHours(s)
  if (hours !== null) {
    const norm = row ? getDayNorm(row, d) : 8
    const ot = Math.max(0, hours - norm)
    return { kind: 'number', hours, norm, regular: Math.min(hours, norm), ot }
  }
  return null
}

// Фоновая подсветка ячейки, если часов больше нормы (жёлтый — есть сверхурочные)
function isOvertimeCell(row, val, d) {
  const data = cellTipData(val, row, d)
  return !!data && data.ot > 0
}

// Текст для пустой ячейки (доступен программно; tooltip для пустых ячеек отключён через :disabled)
function cellTipText(val) {
  if (!val) return 'Ячейка пустая. Кликните для выбора кода.'
  return ''
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

// ИСПРАВЛЕНО: Расчет теперь использует свойство unit из summaryColumns
// Колонки с unit === 'manual' (КДУ) заполняются вручную и здесь не считаются.
// Часы сверх нормы (norm_hours, по умолчанию 8) автоматически уходят в сверхурочные:
// «Итого часов» = все часы; «по тарифу/участку» = только обычные; превышение — в overtime_*.
function cellHoursForDay(row, val) {
  const s = String(val ?? '').trim()
  if (!s) return null
  const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === s.toLowerCase())
  if (codeObj) {
    // код справочника НЕ считаем числовыми часами (например «7» — это Выходной)
    return null
  }
  return rawToHours(s)
}

function normOf(row) {
  const n = Number(row && row.norm_hours)
  return n > 0 ? n : 8
}

function calculateSummary(row) {
  const summary = {}
  summaryColumns.value.forEach(col => { if (col.unit !== 'manual') summary[col.key] = 0 })

  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    const val = String(row.days[d] || '').trim()
    if (!val) continue

    // Норма по графику работы для этого дня недели (fallback: employees.norm_hours или 8)
    const norm = getDayNorm(row, d)

    const hours = cellHoursForDay(row, val)
    if (hours !== null && hours > 0) {
      // числовой ввод: обычные часы + сверхурочные сверх нормы по графику
      const regular = Math.min(hours, norm)
      const ot = Math.max(0, hours - norm)
      summary.total_hours += hours
      summary.fact_days += 1
      summary.tariff_hours += regular
      if (ot > 0) {
        summary.overtime_hours += ot
        summary.overtime_days += 1
      }
      continue
    }

    const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === val.toLowerCase())
    if (codeObj) {
      const hoursDay = Number(codeObj.hours_day) || 0
      const hoursNight = Number(codeObj.hours_night) || 0
      const totalHours = hoursDay + hoursNight
      const dests = codeObj.destinations || []

      dests.forEach(dest => {
        const colDef = summaryColumns.value.find(c => c.key === dest)
        if (colDef && summary.hasOwnProperty(dest)) {
          if (colDef.unit === 'days') {
            summary[dest] += 1
          } else if (dest === 'night_hours') {
            summary[dest] += hoursNight
          } else if (dest === 'day_hours') {
            summary[dest] += hoursDay
          } else {
            summary[dest] += totalHours
          }
        }
      })

      // Распределение по норме для кодов, дающих часы (кроме явно сверхурочных/ночных кодов)
      const isOvertimeCode = dests.includes('overtime_hours') || dests.includes('overtime_days')
      if (hours > 0 && !isOvertimeCode) {
        const ot = Math.max(0, hours - norm)
        if (ot > 0) {
          summary.overtime_hours += ot
          summary.overtime_days += 1
          // из колонок обычных часов вычитаем превышение, если код туда попал
          if (dests.includes('tariff_hours')) summary.tariff_hours -= ot
          if (dests.includes('total_hours')) summary.total_hours = summary.total_hours // итого остаётся полным
        }
      }
    }
  }

  // Округление на основе типа единицы измерения
  for (const key in summary) {
    const colDef = summaryColumns.value.find(c => c.key === key)
    if (colDef) {
      if (colDef.unit === 'hours') {
        summary[key] = Math.round(summary[key] * 100) / 100
      } else {
        summary[key] = Math.round(summary[key]) // Дни всегда целые
      }
    }
  }

  return summary
}

// ===== Ручные колонки КДУ (0..5, точность до сотых) =====
function clampKdu(raw) {
  if (raw === '' || raw === null || raw === undefined) return null
  let n = parseFloat(String(raw).replace(',', '.'))
  if (Number.isNaN(n)) return null
  // автокоррекция: <0 → 0, >5 → 5, округление до сотых (2.567 → 2.57)
  n = Math.min(5, Math.max(0, n))
  return Math.round(n * 100) / 100
}

function onKduInput(row, field, event) {
  const raw = event.target.value
  const clamped = clampKdu(raw)
  row[field] = clamped
  // мгновенная автокоррекция значений вне диапазона (6 → 5)
  if (clamped !== null && String(clamped) !== raw.replace(',', '.')) {
    event.target.value = clamped
  }
  dirtyKdu.value[`${row.employee_id}_${field}`] = clamped
}

function onKduBlur(row, field) {
  const clamped = clampKdu(row[field])
  row[field] = clamped
  dirtyKdu.value[`${row.employee_id}_${field}`] = clamped
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
    // инициализация полей КДУ, если их нет (старые данные)
    ;(data.entries || []).forEach(e => {
      if (!('kdu_work_days' in e)) e.kdu_work_days = null
      if (!('kdu_weekend_days' in e)) e.kdu_weekend_days = null
      // Норма часов: основная — из графика (day_norms по дням месяца);
      // norm_hours сотрудника — только fallback, если график не назначен.
      if (!('norm_hours' in e)) e.norm_hours = null
      if (!e.day_norms) e.day_norms = {}
    })
    tabel.value = data
    dirty.value = {}
    dirtyKdu.value = {}
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

// Сохранение изменённых ячеек дней через PUT /tabels/{id}/cells.
// Возвращает true при успехе (или если изменений нет), иначе выбрасывает ошибку.
async function saveDayCells() {
  const updates = Object.entries(dirty.value).map(([key, value]) => {
    const [empId, day] = key.split('_')
    return { employee_id: Number(empId), day: Number(day), value }
  })
  if (!updates.length) return true
  await api.put(`/tabels/${route.params.id}/cells`, updates)
  dirty.value = {}
  return true
}

// Сохранение ручных значений КДУ отдельно от ячеек дней — через PUT /tabels/{id}/kdu.
async function saveKdu() {
  const kduUpdates = Object.entries(dirtyKdu.value).map(([key, value]) => {
    const idx = key.lastIndexOf('_')
    return { employee_id: Number(key.slice(0, idx)), field: key.slice(idx + 1), value }
  })
  if (!kduUpdates.length) return true
  try {
    await api.put(`/tabels/${route.params.id}/kdu`, kduUpdates)
  } catch (e) {
    // Понятная ошибка, если бэкенд ещё не поддерживает endpoint /kdu
    if (e.response?.status === 404 || e.response?.status === 405) {
      throw new Error('Бэкенд не поддерживает сохранение КДУ (endpoint /tabels/{id}/kdu не найден). Обновите серверную часть.')
    }
    throw e
  }
  dirtyKdu.value = {}
  return true
}

async function save(showMsg = true) {
  const hasCellChanges = Object.keys(dirty.value).length > 0
  const hasKduChanges = Object.keys(dirtyKdu.value).length > 0
  if (!hasCellChanges && !hasKduChanges) return true
  if (Object.keys(cellErrors.value).length) {
    message.value = 'Есть некорректные ячейки — исправьте их перед сохранением'
    messageType.value = 'error'
    return false
  }
  saving.value = true
  try {
    // Ячейки дней и КДУ отправляются раздельно на свои endpoints
    if (hasCellChanges) await saveDayCells()
    if (hasKduChanges) await saveKdu()
    if (showMsg) {
      message.value = 'Сохранено'
      messageType.value = 'success'
      setTimeout(() => { if (message.value === 'Сохранено') message.value = '' }, 2000)
    }
    return true
  } catch (e) {
    message.value = e.response?.data?.detail || e.message || 'Ошибка сохранения'
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

function editCode(c) {
  isEditing.value = true
  editingCode.value = c
  newCode.value = {
    code: c.code,
    name: c.name,
    hours_day: c.hours_day,
    hours_night: c.hours_night,
    destinations: [...(c.destinations || [])]
  }
  codeError.value = ''
}

function cancelEdit() {
  isEditing.value = false
  editingCode.value = null
  newCode.value = { code: '', name: '', hours_day: 0, hours_night: 0, destinations: [] }
  codeError.value = ''
}

async function saveCode() {
  codeError.value = ''
  try {
    if (isEditing.value && editingCode.value) {
      await api.put(`/time-codes/${editingCode.value.id}`, newCode.value)
    } else {
      await api.post('/time-codes/', newCode.value)
    }
    cancelEdit()
    await loadCodes()
  } catch (e) {
    codeError.value = typeof e.response?.data?.detail === 'string'
      ? e.response.data.detail : 'Ошибка сохранения кода'
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
/* Tooltip для ячеек табеля */
.day-tooltip {
  font-size: 12px;
  line-height: 1.5;
  padding: 4px 2px;
}
.tooltip-divider {
  opacity: 0.3;
}
.cell-tip-area {
  display: block;
  width: 100%;
  height: 100%;
}
.tabel-table {
  border-collapse: collapse;
  font-size: 12px;
  white-space: nowrap;
}
.tabel-table th, .tabel-table td {
  border: 1px solid #000;
  padding: 2px;
}

.tabel-table thead th {
  background-color: white !important;
  color: black !important;
  font-weight: bold;
  text-align: center;
  vertical-align: middle;
}

.col-no { width: 40px; text-align: center; font-size: 11px; }
.col-fio { min-width: 200px; text-align: left; padding-left: 6px !important; }
.col-days-header { font-size: 13px; font-weight: bold; padding: 4px !important; }
.col-day-header { width: 38px; min-width: 38px; max-width: 38px; padding: 2px 1px !important; font-size: 10px; }
.day-name { font-size: 9px; font-weight: normal; color: #666; }
.day-number { font-size: 11px; font-weight: bold; }
.day-weekend-header { background-color: #f0f0f0 !important; }
.day-holiday-header { background-color: #fff3cd !important; }

.col-summary-header {
  width: 28px; min-width: 28px; max-width: 28px; padding: 8px 2px !important;
  font-size: 10px; font-weight: bold; text-align: center;
  writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg);
  white-space: nowrap; vertical-align: middle;
  background-color: white !important; border-left: 1px solid #000 !important;
}

.col-summary-cell {
  width: 28px; min-width: 28px; max-width: 28px; padding: 2px 1px !important;
  font-size: 11px; font-weight: normal; text-align: center;
  background-color: white !important; border-left: 1px solid #000 !important;
}

/* Ручные колонки КДУ — визуально отличаются (зелёный фон input) */
.kdu-input {
  width: 100%; box-sizing: border-box;
  border: 1px solid #a5d6a7; border-radius: 4px;
  background-color: #e8f5e9;
  font-size: 11px; text-align: center; padding: 2px 1px;
  outline: none;
}
.kdu-input:focus { border-color: #2e7d32; background-color: #f1f8e9; }
/* скрыть стрелки number-инпута, чтобы не ломать узкую колонку */
.kdu-input::-webkit-outer-spin-button,
.kdu-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.kdu-input[type=number] { -moz-appearance: textfield; appearance: textfield; }

.col-del { width: 40px; background-color: white !important; }
.cell-day { width: 38px; min-width: 38px; max-width: 38px; padding: 2px !important; }
.cell-weekend { background-color: #f0f0f0; }
.cell-holiday { background-color: #fff3cd; }
.holiday-mark { font-size: 10px; margin-left: 1px; vertical-align: top; }

.legend-box { display: inline-block; width: 14px; height: 14px; border-radius: 3px; border: 1px solid #c8e6c9; vertical-align: middle; margin-right: 4px; }
.legend-weekend { background-color: #f0f0f0; }
.legend-holiday { background-color: #fff3cd; }

.cell-wrap { position: relative; width: 100%; height: 24px; }
.cell-input {
  width: 100%; height: 24px; box-sizing: border-box; border: none; outline: none;
  background: transparent; text-align: center; font-size: 12px; font-family: inherit;
  cursor: pointer; color: rgba(0, 0, 0, 0.87);
}
.cell-input:hover { background: #e8f5e9; }
.cell-wrap.is-open .cell-input { background: #e8f5e9; box-shadow: inset 0 0 0 2px #2d5a3d; }
.is-code { color: #1565c0; font-weight: bold; }
/* Ячейка с часами сверх нормы (есть сверхурочные) — жёлтая подсветка */
.is-overtime-cell { background: #fff9c4 !important; box-shadow: inset 0 -2px 0 #f9a825; }
.is-error, .is-error-cell { background: #ffebee !important; outline: 2px solid red; }
.add-row td { border-top: 2px dashed #a5d6a7; background: #f9fbe7; }
.add-cell { padding: 6px 8px !important; }

/* Стили для справочника кодов часов */
.code-row { transition: background-color 0.2s ease; }
.code-row:hover { background-color: #f5f5f5 !important; }
.code-row .v-btn { opacity: 1 !important; transition: transform 0.2s ease, background-color 0.2s ease; }
.code-row .v-btn:hover { transform: scale(1.15); background-color: rgba(0, 0, 0, 0.04) !important; }
</style>

<style>
.cell-menu .v-overlay__content { background: white; border-radius: 8px; }
</style>