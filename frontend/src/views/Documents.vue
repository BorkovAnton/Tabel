<template>
  <v-container fluid>
    <div class="d-flex align-center flex-wrap ga-3 mb-4">
      <h2 class="text-h5"><v-icon icon="mdi-file-document-edit-outline" class="mr-2" color="#2d5a3d" />Документы и приказы</h2>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">Добавить документ</v-btn>
    </div>

    <!-- Фильтры -->
    <v-row dense class="mb-2">
      <v-col cols="12" sm="4" md="3">
        <v-text-field
          v-model="searchEmp"
          label="Сотрудник (поиск)"
          density="compact"
          variant="outlined"
          append-icon="mdi-magnify"
          clearable
          hide-details
          @update:model-value="onEmpSearch"
        >
          <template #append><v-icon @click="loadDocuments">mdi-magnify</v-icon></template>
        </v-text-field>
      </v-col>
      <v-col cols="6" sm="4" md="3">
        <v-autocomplete
          v-model="filterType"
          :items="typeItems"
          item-title="title"
          item-value="value"
          label="Тип события (код часов)"
          density="compact"
          variant="outlined"
          autocomplete="off"
          clearable
          hide-details
          :filter="filterCodesByTitle"
          @update:model-value="loadDocuments"
        />
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-select
          v-model="filterMonth"
          :items="monthItems"
          item-title="title"
          item-value="value"
          label="Месяц"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="loadDocuments"
        />
      </v-col>
      <v-col cols="12" sm="4" md="2">
        <v-checkbox
          v-model="showInactive"
          label="Показывать отключённые"
          density="compact"
          hide-details
          class="mt-2"
          @update:model-value="loadDocuments"
        />
      </v-col>
    </v-row>

    <v-alert v-if="message" :type="messageType" density="compact" variant="tonal" class="mb-3" closable @update:model-value="message = ''">
      {{ message }}
    </v-alert>

    <v-table class="bg-white rounded">
      <thead>
        <tr>
          <th>Сотрудник</th>
          <th>Тип</th>
          <th>Период</th>
          <th>Код</th>
          <th>Номер</th>
          <th>Комментарий</th>
          <th>Активен</th>
          <th style="width: 120px">Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!docs.length">
          <td colspan="8" class="text-center text-grey py-6">Нет документов за выбранный месяц</td>
        </tr>
        <tr v-for="d in docs" :key="d.id" :class="{ 'text-grey': !d.is_active }">
          <td>{{ d.employee_full_name }}<div class="text-caption text-grey">Таб. {{ d.employee_tab_number }}</div></td>
          <td><v-chip size="x-small" label :color="chipColor(d)">{{ docTypeLabel(d.doc_type) }}</v-chip></td>
          <td class="text-no-wrap">{{ fmtDate(d.start_date) }} — {{ fmtDate(d.end_date) }}</td>
          <td><v-chip size="x-small" label :color="chipColor(d)">{{ d.code }}</v-chip></td>
          <td>{{ d.doc_number || '—' }}</td>
          <td class="text-caption">{{ d.title || '—' }}</td>
          <td>
            <v-switch
              :model-value="d.is_active"
              density="compact"
              hide-details
              color="success"
              @update:model-value="toggleActive(d, $event)"
            />
          </td>
          <td>
            <v-btn size="x-small" variant="text" prepend-icon="mdi-pencil" @click="openEdit(d)">Изменить</v-btn>
            <v-btn size="x-small" variant="text" color="error" prepend-icon="mdi-delete-outline" @click="removeDoc(d)">Удалить</v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <!-- Диалог создания/редактирования -->
    <v-dialog v-model="editDialog" max-width="560">
      <v-card>
        <v-card-title>{{ isEditing ? 'Редактировать документ' : 'Добавить документ' }}</v-card-title>
        <v-card-text>
          <v-autocomplete
            v-model="form.employee_id"
            :items="employeeOptions"
            item-title="label"
            item-value="id"
            label="Сотрудник (поиск по ФИО / таб. номеру)"
            density="compact"
            variant="outlined"
            autocomplete="off"
            class="mb-2"
            clearable
            :filter="filterEmployees"
            :menu-props="{ maxHeight: 320 }"
            :rules="[v => !!v || 'Выберите сотрудника']"
          />
          <v-autocomplete
            v-model="form.doc_type"
            :items="typeItems"
            item-title="title"
            item-value="value"
            label="Тип события (код часов)"
            density="compact"
            variant="outlined"
            autocomplete="off"
            class="mb-2"
            clearable
            :filter="filterCodesByTitle"
            :menu-props="{ maxHeight: 320 }"
            :rules="[v => !!v || 'Выберите тип события']"
            @update:model-value="onTypeChange"
          >
            <!-- В списке: чип с кодом + название + часы дня/ночи -->
            <template #item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps" :title="null">
                <div class="d-flex align-center ga-2 text-truncate">
                  <v-chip size="x-small" label :color="CATEGORY_COLORS[item.raw.category]">{{ item.raw.code }}</v-chip>
                  <span class="text-truncate">{{ item.raw.name }}</span>
                  <span class="text-caption text-grey ml-auto text-no-wrap">День: {{ fmtH(item.raw.hours_day) }} | Ночь: {{ fmtH(item.raw.hours_night) }}</span>
                </div>
              </v-list-item>
            </template>
            <!-- Выбранный тип отображается как чип с кодом + название -->
            <template #selection="{ item }">
              <v-chip size="small" label :color="CATEGORY_COLORS[item.raw.category]">
                {{ item.raw.code }} — {{ item.raw.name }}
              </v-chip>
            </template>
          </v-autocomplete>
          <div class="d-flex ga-2 mb-2">
            <v-text-field
              v-model="form.start_date"
              label="Дата начала"
              type="date"
              density="compact"
              variant="outlined"
              class="flex-grow-1"
            />
            <v-text-field
              v-model="form.end_date"
              label="Дата окончания"
              type="date"
              density="compact"
              variant="outlined"
              class="flex-grow-1"
            />
          </div>
          <div class="text-caption text-grey mb-2" v-if="daysCount !== null">
            Дней в периоде: {{ daysCount }}
          </div>
          <v-autocomplete
            v-model="form.code"
            :items="codeItems"
            item-title="title"
            item-value="value"
            label="Код часов (поиск по коду / названию, подставляется автоматически по типу)"
            density="compact"
            variant="outlined"
            autocomplete="off"
            class="mb-2"
            clearable
            :filter="filterCodes"
            :menu-props="{ maxHeight: 320 }"
            :rules="[v => !!v || 'Укажите код']"
          />
          <v-text-field
            v-model.number="form.hours"
            label="Часы события (автоподставлены из кода, можно изменить)"
            type="number"
            step="0.25"
            min="0"
            density="compact"
            variant="outlined"
            class="mb-2"
            clearable
            hint="Напр. 8 — сколько часов засчитать за каждый день периода в отчёте по часам"
            persistent-hint
          />
          <v-text-field v-model="form.doc_number" label="Номер приказа / больничного" density="compact" variant="outlined" class="mb-2" />
          <v-textarea v-model="form.title" label="Комментарий" density="compact" variant="outlined" rows="2" />
          <v-checkbox v-model="form.is_active" label="Документ активен (учитывается при автозаполнении)" density="compact" hide-details />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="editDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveDoc">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'

const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

// «Тип события» — это код из справочника «Коды часов» (О, К, Б, 8с и т.д.).
// Внутренняя категория (для цвета чипа) определяется по коду/названию кода.
const CATEGORY_BY_CODE = { 'О': 'vacation', 'К': 'business_trip', 'Б': 'sick', 'Н': 'sick' }
const CATEGORY_COLORS = { vacation: 'success', business_trip: 'primary', sick: 'warning', other: '#2d5a3d' }
const CATEGORY_TITLES = { vacation: 'Отпуск', business_trip: 'Командировка', sick: 'Больничный', other: 'Другое' }

function fmtH(v) {
  const n = Number(v) || 0
  if (!n) return '0ч'
  return Number.isInteger(n) ? `${n}ч` : `${Math.floor(n)}ч${Math.round((n - Math.floor(n)) * 60)}м`
}

function normCat(s) {
  return String(s ?? '').toLowerCase().replace(/ё/g, 'е').trim()
}

// Категория по коду справочника: явное соответствие или по названию кода
function categoryForCode(code, name) {
  const c = String(code ?? '').trim().toUpperCase()
  if (CATEGORY_BY_CODE[c]) return CATEGORY_BY_CODE[c]
  const nm = normCat(name)
  if (nm.includes('отпуск') || nm.includes('очен')) return 'vacation'
  if (nm.includes('командиров')) return 'business_trip'
  if (nm.includes('больничн') || nm.includes('нетрудосп') || nm.includes('болезн')) return 'sick'
  return 'other'
}

// Часы кода для автоподстановки в документ:
// фиксированные hours_day+hours_night; если «Время по графику» — weekend_hours или 8
function codeEventHours(c) {
  if (!c) return null
  const sum = (Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)
  if (sum > 0) return sum
  if (c.use_schedule_hours) return Number(c.weekend_hours) || 8
  return null
}

// Элементы выпадающего списка «Тип события» — из справочника «Коды часов»
const typeItems = computed(() => timeCodes.value.map(c => ({
  code: c.code,
  name: c.name,
  title: `${c.code} — ${c.name} | День: ${fmtH(c.hours_day)} | Ночь: ${fmtH(c.hours_night)}`,
  value: c.code,
  category: categoryForCode(c.code, c.name),
  raw: c,
})))

// Справочник категорий по коду (для старых документов без doc_type_category)
const categoryByCode = computed(() => {
  const m = {}
  for (const it of typeItems.value) m[it.code.toUpperCase()] = it.category
  return m
})

const LEGACY_CATEGORY = { vacation: 'vacation', business_trip: 'business_trip', sick: 'sick', other: 'other' }

function docCategory(d) {
  if (d.doc_type_category && CATEGORY_COLORS[d.doc_type_category]) return d.doc_type_category
  const dt = String(d.doc_type ?? '')
  // старые документы: doc_type хранится как категория ('vacation' и т.п.)
  if (LEGACY_CATEGORY[dt]) return LEGACY_CATEGORY[dt]
  return categoryByCode.value[dt.toUpperCase()] || categoryForCode(dt, '')
}

function chipColor(d) {
  return CATEGORY_COLORS[docCategory(d)] || CATEGORY_COLORS.other
}

function docTypeLabel(v) {
  const code = String(v ?? '').trim()
  const tc = timeCodes.value.find(c => c.code === code)
  if (tc) return `${code} — ${tc.name}`
  // старые документы: doc_type — это категория ('vacation' и т.п.)
  if (LEGACY_CATEGORY[code]) return CATEGORY_TITLES[LEGACY_CATEGORY[code]] || code
  const cat = categoryByCode.value[code.toUpperCase()] || categoryForCode(code, '')
  return `${code} (${CATEGORY_TITLES[cat] || 'Другое'})`
}

const docs = ref([])
const employees = ref([])
const timeCodes = ref([])
const filterType = ref(null)
const searchEmp = ref('')
const showInactive = ref(false)

// Месяц по умолчанию — текущий (октябрь 2026)
const now = new Date()
const filterMonth = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const monthItems = computed(() => {
  const items = []
  // ±12 месяцев от текущего
  for (let i = -12; i <= 12; i++) {
    const dt = new Date(now.getFullYear(), now.getMonth() + i, 1)
    items.push({
      title: `${monthNames[dt.getMonth()]} ${dt.getFullYear()}`,
      value: `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`,
    })
  }
  return items
})

const editDialog = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const saving = ref(false)
const message = ref('')
const messageType = ref('success')

const form = ref({
  employee_id: null,
  doc_type: 'О',               // код из справочника «Коды часов» (тип события)
  doc_type_category: 'vacation', // внутренняя категория — для цвета чипа
  start_date: '',
  end_date: '',
  code: 'О',                   // подставляется автоматически из типа события
  hours: null,                 // часы события (автоподстановка из кода, можно изменить)
  doc_number: '',
  title: '',
  is_active: true,
})

const codeItems = computed(() =>
  timeCodes.value.map(c => ({
    title: `${c.code} — ${c.name}`,
    value: c.code,
  })))

// Поиск по коду/названию (регистронезависимо, Ё->Е) — как в заполнении табеля
function filterCodes(item, query) {
  const q = String(query ?? '').toLowerCase().replace(/ё/g, 'е')
  if (!q) return true
  return String(item.title ?? '').toLowerCase().replace(/ё/g, 'е').includes(q)
}

// То же для элементов typeItems (raw — объект кода справочника)
function filterCodesByTitle(item, query) {
  return filterCodes(item, query)
}

const daysCount = computed(() => {
  if (!form.value.start_date || !form.value.end_date) return null
  const a = new Date(form.value.start_date), b = new Date(form.value.end_date)
  if (isNaN(a) || isNaN(b) || b < a) return null
  return Math.round((b - a) / 86400000) + 1
})

function fmtDate(s) {
  if (!s) return ''
  const [y, m, d] = String(s).split('-')
  return `${d}.${m}.${y}`
}

// Выбор «Типа события» (код из справочника): автоматически подставляем
// соответствующий код в поле «Код часов», категорию и часы события.
function onTypeChange(v) {
  const tc = timeCodes.value.find(c => c.code === v)
  if (!tc) return
  form.value.code = tc.code                                   // автоподстановка кода
  form.value.doc_type_category = categoryForCode(tc.code, tc.name)
  form.value.hours = codeEventHours(tc)                       // часы из кода (редактируемы)
}

function onEmpSearch() { /* поиск применяется в loadDocuments через selected employee */ }

// Нормализация для поиска: нижний регистр + Ё->Е (как в заполнении табеля)
const normSearch = s => String(s ?? '').toLowerCase().replace(/ё/g, 'е')

function empMatches(e, term) {
  const t = normSearch(term)
  return (
    normSearch(e.full_name).includes(t) ||
    normSearch(e.tab_number).includes(t) ||
    normSearch(e.department_name).includes(t)
  )
}

// Фильтрация внутри v-autocomplete: поиск по ФИО / табельному / подразделению
function filterEmployees(item, query) {
  if (!query || !String(query).trim()) return true
  const e = item.raw ?? item
  return empMatches(e, query)
}

const employeeOptions = computed(() =>
  employees.value.map(e => ({
    ...e,
    label: `${e.full_name}${e.tab_number ? ' — Таб. ' + e.tab_number : ''}${e.department_name ? ' — ' + e.department_name : ''}`
  }))
)

async function loadEmployees() {
  try {
    const { data } = await api.get('/tabels/search/employees', { params: { q: '', limit: 1000 } })
    employees.value = (Array.isArray(data) ? data : []).map(e => ({
      id: e.id,
      full_name: e.full_name,
      tab_number: e.tab_number,
      department_name: e.department_name,
      label: `${e.full_name} (Таб. ${e.tab_number})`,
    })).sort((a, b) => a.label.localeCompare(b.label, 'ru'))
  } catch (e) { /* ignore */ }
}

async function loadCodes() {
  try {
    const { data } = await api.get('/time-codes/')
    timeCodes.value = (data || []).filter(c => c.is_active !== false)
  } catch (e) { /* ignore */ }
}

async function loadDocuments() {
  try {
    const [y, m] = String(filterMonth.value).split('-').map(Number)
    const params = { year: y, month: m, include_inactive: showInactive.value }
    if (filterType.value) params.doc_type = filterType.value
    // фильтр по сотруднику — матчинг по подстроке из локального списка
    let empIds = null
    if (searchEmp.value && searchEmp.value.trim()) {
      const q = searchEmp.value.trim().toLowerCase()
      empIds = employees.value
        .filter(e => e.label.toLowerCase().includes(q))
        .map(e => e.id)
      if (!empIds.length) { docs.value = []; return }
    }
    const { data } = await api.get('/documents/', { params })
    let list = data || []
    if (empIds) list = list.filter(d => empIds.includes(d.employee_id))
    docs.value = list
  } catch (e) {
    const detail = typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Ошибка загрузки документов'
    message.value = detail
    messageType.value = 'error'
  }
}

function openCreate() {
  isEditing.value = false
  editingId.value = null
  const today = new Date()
  const mm = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-`
  form.value = {
    employee_id: null,
    doc_type: 'О',
    doc_type_category: 'vacation',
    start_date: `${mm}${String(today.getDate()).padStart(2, '0')}`,
    end_date: `${mm}${String(today.getDate()).padStart(2, '0')}`,
    code: 'О',
    hours: null,
    doc_number: '',
    title: '',
    is_active: true,
  }
  // автоподстановка часов из кода «О», если он есть в справочнике
  const def = timeCodes.value.find(c => c.code === 'О')
  if (def) form.value.hours = codeEventHours(def)
  editDialog.value = true
}

function openEdit(d) {
  isEditing.value = true
  editingId.value = d.id
  form.value = {
    employee_id: d.employee_id,
    doc_type: d.doc_type,                 // код из справочника («Тип события»)
    doc_type_category: d.doc_type_category || docCategory(d),
    start_date: d.start_date,
    end_date: d.end_date,
    code: d.code,
    hours: d.hours ?? null,
    doc_number: d.doc_number || '',
    title: d.title || '',
    is_active: d.is_active,
  }
  editDialog.value = true
}

async function saveDoc() {
  message.value = ''
  if (!form.value.employee_id || !form.value.doc_type || !form.value.code || !form.value.start_date || !form.value.end_date) {
    message.value = 'Заполните сотрудника, тип события, период и код'
    messageType.value = 'error'
    return
  }
  if (form.value.end_date < form.value.start_date) {
    message.value = 'Дата окончания должна быть не раньше даты начала'
    messageType.value = 'error'
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value }
    if (isEditing.value) {
      await api.put(`/documents/${editingId.value}`, payload)
    } else {
      await api.post('/documents/', payload)
    }
    editDialog.value = false
    message.value = 'Документ сохранён'
    messageType.value = 'success'
    await loadDocuments()
  } catch (e) {
    const detail = typeof e.response?.data?.detail === 'string'
      ? e.response.data.detail
      : (Array.isArray(e.response?.data?.detail) ? e.response.data.detail.map(x => x.msg || x).join('; ') : 'Ошибка сохранения')
    message.value = detail
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

async function toggleActive(d, val) {
  try {
    await api.put(`/documents/${d.id}`, { is_active: !!val })
    d.is_active = !!val
  } catch (e) {
    message.value = 'Не удалось изменить статус документа'
    messageType.value = 'error'
  }
}

async function removeDoc(d) {
  if (!confirm(`Удалить документ «${docTypeLabel(d.doc_type)}» (${fmtDate(d.start_date)} — ${fmtDate(d.end_date)}) для ${d.employee_full_name}?`)) return
  try {
    await api.delete(`/documents/${d.id}`)
    await loadDocuments()
  } catch (e) {
    message.value = 'Не удалось удалить документ'
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await Promise.all([loadEmployees(), loadCodes(), loadDocuments()])
})
</script>

<style scoped>
.text-no-wrap { white-space: nowrap; }
</style>
