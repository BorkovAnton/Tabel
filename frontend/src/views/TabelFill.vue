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

    <div style="overflow-x:auto; border:1px solid #c8e6c9; border-radius:8px; background:white;">
      <table class="tabel-table" v-if="tabel.entries.length">
        <thead>
          <tr>
            <th class="col-no sticky-col">№</th>
            <th class="col-fio sticky-col2">ФИО / табельный</th>
            <th v-for="d in tabel.days_in_month" :key="d" class="col-day">{{ d }}</th>
            <th class="col-sum">Итого</th>
            <th class="col-del"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in tabel.entries" :key="row.employee_id">
            <td class="col-no sticky-col">{{ idx + 1 }}</td>
            <td class="col-fio sticky-col2" :title="row.full_name">
              {{ row.full_name }}<br /><small class="text-grey">{{ row.tab_number }}</small>
            </td>
            <td v-for="d in tabel.days_in_month" :key="d" class="cell-day">
              <v-combobox
                :model-value="row.days[d]"
                :items="cellItems"
                item-title="title"
                item-value="value"
                menu-icon=""
                clearable
                dense
                variant="plain"
                hide-details
                auto-select-first
                return-object
                class="cell-combo"
                :class="{ 'is-error-cell': hasError(row.employee_id, d) }"
                placeholder=""
                @update:model-value="(v) => onCellChange(row.employee_id, d, v)"
              >
                <template #selection="{ item }">
                  <span :class="['cell-text', { 'is-code': isCodeText(item.raw.value ?? item.title) }]">
                    {{ shortLabel(item.raw.value ?? item.title) }}
                  </span>
                </template>
                <template #item="{ props: p, item }">
                  <v-list-item v-bind="p" :title="item.raw.title" />
                </template>
              </v-combobox>
            </td>
            <td class="col-sum text-center">{{ totalHours(row) }}</td>
            <td class="col-del">
              <span class="code-chips" v-if="codesForRow(row).length">
                <v-chip v-for="c in codesForRow(row)" :key="c.code" size="x-small"
                        variant="tonal" color="#2d5a3d" style="margin:1px;">{{ c.code }}</v-chip>
              </span>
              <a href="#" class="text-red text-caption" style="white-space:nowrap;"
                 @click.prevent="removeEmployee(row)">Удалить</a>
            </td>
          </tr>

          <!-- Строка добавления сотрудника: появляется под списком и «съезжает» вниз -->
          <tr class="add-row">
            <td class="sticky-col"></td>
            <td class="sticky-col2 add-cell">
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
            <td :colspan="tabel.days_in_month + 2"></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="pa-4">
        <!-- Табель пуст — форма добавления видна сразу -->
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

    <!-- Справочник «Коды часов» (редактирование — только для Администратора) -->
    <v-dialog v-model="codesDialog" max-width="720">
      <v-card title="Справочник «Коды часов»">
        <v-card-text>
          <v-table density="compact">
            <thead>
              <tr><th>Код</th><th>Наименование</th><th>Часов день</th><th>Часов ночь</th><th v-if="auth.isAdmin"></th></tr>
            </thead>
            <tbody>
              <tr v-for="c in timeCodes" :key="c.id">
                <td><b>{{ c.code }}</b></td>
                <td>{{ c.name }}</td>
                <td>{{ c.hours_day }}</td>
                <td>{{ c.hours_night }}</td>
                <td v-if="auth.isAdmin"><v-btn size="x-small" icon="mdi-delete" color="red" variant="text" @click="deleteCode(c)" /></td>
              </tr>
            </tbody>
          </v-table>
          <template v-if="auth.isAdmin">
            <v-form @submit.prevent="addCode" class="d-flex mt-4" style="gap:8px;">
              <v-text-field v-model="newCode.code" label="Код" density="compact" variant="outlined" style="max-width:100px;" hide-details />
              <v-text-field v-model="newCode.name" label="Наименование" density="compact" variant="outlined" hide-details />
              <v-text-field v-model.number="newCode.hours_day" label="День" type="number" step="0.01" density="compact" variant="outlined" style="max-width:100px;" hide-details />
              <v-text-field v-model.number="newCode.hours_night" label="Ночь" type="number" step="0.01" density="compact" variant="outlined" style="max-width:100px;" hide-details />
              <v-btn color="#2d5a3d" type="submit" prepend-icon="mdi-plus">Добавить</v-btn>
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

const tabel = ref(null)
const timeCodes = ref([])
const dirty = ref({})           // { "empId_day": value }
const cellErrors = ref({})      // { "empId_day": true }
const message = ref('')
const messageType = ref('success')
const saving = ref(false)

const codesDialog = ref(false)
const newCode = ref({ code: '', name: '', hours_day: 0, hours_night: 0 })
const codeError = ref('')

// --- поиск сотрудников в выпадающем списке ---
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
  // исключаем уже добавленных в табель
  const inTabel = new Set((tabel.value?.entries || []).map(r => r.employee_id))
  allEmployees.value = data.filter(e => !inTabel.has(e.id))
}

// выбор из списка сразу добавляет строку вниз таблицы
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
  // код из справочника (в т.ч. «8н», «8с») — подсвечиваем синим
  return !!v && codeSet().has(String(v).trim().toLowerCase())
}
function shortLabel(v) {
  // в самой ячейке показываем только код/число, без длинного описания
  return String(v ?? '')
}

// Список для ячеек: все коды часов + типовые значения часов.
// v-combobox фильтрует его по подстроке: наберите «8» — останутся 8, 8н, 8с и т.д.
const cellItems = computed(() => {
  const items = timeCodes.value.map(c => ({
    title: `${c.code} — ${c.name} (день ${c.hours_day} / ночь ${c.hours_night})`,
    value: c.code,
  }))
  for (const h of [0.25, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 23.59]) {
    const s = String(h).replace('.', ',')
    items.push({ title: `${s} ч.`, value: s })
  }
  return items
})

// выбор/ввод значения ячейки
function onCellChange(empId, day, val) {
  let text = ''
  if (val !== null && val !== undefined) {
    text = (typeof val === 'object') ? String(val.value ?? val.title ?? '') : String(val)
  }
  text = text.trim()
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  if (row) row.days[day] = text
  markDirty(empId, day)
  validateCell(empId, day)
}
function isValidValue(v) {
  if (!v || !v.trim()) return true
  const s = v.trim().replace(',', '.')
  // сначала точное совпадение с кодом справочника (важно для «8н», «8с»)
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
function totalHours(row) {
  let sum = 0
  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    const v = (row.days[d] || '').trim().replace(',', '.')
    if (/^\d+(\.\d+)?$/.test(v)) sum += parseFloat(v)
    else if (v) {
      const c = timeCodes.value.find(x => x.code.toLowerCase() === v.toLowerCase())
      if (c) sum += (c.hours_day || 0) + (c.hours_night || 0)
    }
  }
  return Math.round(sum * 100) / 100
}

async function loadTabel() {
  // id берём из маршрута; защищаемся от нечисловых значений (422 на бэкенде)
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
    // 401 — протух токен: на страницу входа
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
  // Чтение справочника «Коды часов» доступно всем авторизованным;
  // изменение/удаление записей — только Администратору (проверяется на бэкенде).
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
    newCode.value = { code: '', name: '', hours_day: 0, hours_night: 0 }
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

// автосохранение каждые 30 сек, если есть несохранённые изменения
setInterval(() => { if (Object.keys(dirty.value).length) save(false) }, 30000)

onMounted(async () => {
  await Promise.all([loadTabel(), loadCodes()])
  await loadEmployees()
})
</script>

<style scoped>
.tabel-table {
  border-collapse: collapse;
  font-size: 13px;
  white-space: nowrap;
}
.tabel-table th, .tabel-table td {
  border: 1px solid #c8e6c9;
  padding: 2px;
}
.tabel-table thead th {
  background-color: #2d5a3d !important;
  color: white !important;
  position: sticky;
  top: 0;
  z-index: 3;
}
.col-no { width: 36px; text-align: center; }
.col-fio { min-width: 220px; text-align: left; padding-left: 8px !important; }
.col-day { width: 42px; text-align: center; }
.col-sum { width: 60px; }
.sticky-col { position: sticky; left: 0; background: #f1f8e9; z-index: 2; }
.sticky-col2 { position: sticky; left: 36px; background: #f1f8e9; z-index: 2; }
thead .sticky-col, thead .sticky-col2 { z-index: 4; background: #2d5a3d !important; }
/* ячейка табеля — combobox с выбором из списка кодов/часов */
.cell-combo { min-width: 40px; }
.cell-combo :deep(.v-field) { background: transparent; box-shadow: none !important; }
.cell-combo :deep(.v-field__field), .cell-combo :deep(input) { text-align: center; }
.cell-combo :deep(.v-field__input) {
  text-align: center;
  font-size: 13px;
  padding: 0 2px !important;
  min-height: 26px !important;
  height: 26px !important;
}
.cell-combo :deep(.v-field__append-inner) { display: none; }
.cell-text { font-size: 13px; }
.is-code { color: #1565c0; font-weight: bold; }
.is-error, .is-error-cell { background: #ffebee; outline: 2px solid red; }
.add-row td { border-top: 2px dashed #a5d6a7; background: #f9fbe7; }
.add-cell { padding: 6px 8px !important; }
</style>
