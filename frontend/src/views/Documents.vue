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
        <v-select
          v-model="filterType"
          :items="docTypeItems"
          label="Тип события"
          density="compact"
          variant="outlined"
          clearable
          hide-details
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
          <td>{{ docTypeLabel(d.doc_type) }}</td>
          <td class="text-no-wrap">{{ fmtDate(d.start_date) }} — {{ fmtDate(d.end_date) }}</td>
          <td><v-chip size="x-small" label color="#2d5a3d">{{ d.code }}</v-chip></td>
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
          <v-select
            v-model="form.employee_id"
            :items="employees"
            item-title="label"
            item-value="id"
            label="Сотрудник"
            density="compact"
            variant="outlined"
            autocomplete="off"
            class="mb-2"
            :rules="[v => !!v || 'Выберите сотрудника']"
          />
          <v-select
            v-model="form.doc_type"
            :items="docTypeItems"
            label="Тип события"
            density="compact"
            variant="outlined"
            class="mb-2"
            @update:model-value="onTypeChange"
          />
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
          <v-select
            v-model="form.code"
            :items="codeItems"
            label="Код часов (подставляется автоматически по типу)"
            density="compact"
            variant="outlined"
            class="mb-2"
            :rules="[v => !!v || 'Укажите код']"
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

const DOC_TYPES = [
  { value: 'vacation', title: 'Отпуск', code: 'О' },
  { value: 'business_trip', title: 'Командировка', code: 'К' },
  { value: 'sick', title: 'Больничный', code: 'Б' },
  { value: 'other', title: 'Другое', code: '' },
]
const docTypeItems = DOC_TYPES.map(t => ({ title: t.title, value: t.value }))

function docTypeLabel(v) {
  return DOC_TYPES.find(t => t.value === v)?.title || v
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
  doc_type: 'vacation',
  start_date: '',
  end_date: '',
  code: 'О',
  doc_number: '',
  title: '',
  is_active: true,
})

const codeItems = computed(() =>
  timeCodes.value.map(c => ({
    title: `${c.code} — ${c.name}`,
    value: c.code,
  })))

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

function onTypeChange(v) {
  const t = DOC_TYPES.find(x => x.value === v)
  if (t && t.code) form.value.code = t.code   // автоподстановка кода по типу
}

function onEmpSearch() { /* поиск применяется в loadDocuments через selected employee */ }

async function loadEmployees() {
  try {
    const { data } = await api.get('/employees/')
    employees.value = (data || []).map(e => ({
      id: e.id,
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
    doc_type: 'vacation',
    start_date: `${mm}${String(today.getDate()).padStart(2, '0')}`,
    end_date: `${mm}${String(today.getDate()).padStart(2, '0')}`,
    code: 'О',
    doc_number: '',
    title: '',
    is_active: true,
  }
  editDialog.value = true
}

function openEdit(d) {
  isEditing.value = true
  editingId.value = d.id
  form.value = {
    employee_id: d.employee_id,
    doc_type: d.doc_type,
    start_date: d.start_date,
    end_date: d.end_date,
    code: d.code,
    doc_number: d.doc_number || '',
    title: d.title || '',
    is_active: d.is_active,
  }
  editDialog.value = true
}

async function saveDoc() {
  message.value = ''
  if (!form.value.employee_id || !form.value.code || !form.value.start_date || !form.value.end_date) {
    message.value = 'Заполните сотрудника, период и код'
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
