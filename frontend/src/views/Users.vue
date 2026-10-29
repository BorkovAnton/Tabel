<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h2 class="text-h5" style="font-weight:bold;">Пользователи и роли</h2>
      <v-spacer />
      <v-btn color="#2d5a3d" prepend-icon="mdi-account-plus" @click="openCreate">Добавить пользователя</v-btn>
    </div>

    <v-alert v-if="error" type="error" density="compact" class="mb-3" closable @click:close="error=''">{{ error }}</v-alert>

    <v-data-table :headers="headers" :items="users" :loading="loading" hover class="rounded-lg">
      <template #item.roles="{ item }">
        <!-- ✅ ЭТАП 8: чип роли только по новой системе (role) -->
        <v-chip v-if="item.role" size="x-small" :color="roleChipColor(item.role)" variant="toned" class="mr-1">{{ roleTitle(item.role) }}</v-chip>
        <span v-if="!item.role" class="text-grey text-caption">—</span>
      </template>
      <template #item.departments="{ item }">
        <span v-if="item.all_departments" class="text-caption" style="color:#2d5a3d;">Все подразделения</span>
        <template v-else-if="item.allowed_department_names?.length">
          <v-chip v-for="d in item.allowed_department_names" :key="d" size="x-small" variant="toned"
                  color="blue-grey" class="mr-1 mb-1">{{ d }}</v-chip>
        </template>
        <span v-else class="text-grey text-caption">—</span>
      </template>
      <template #item.actions="{ item }">
        <CustomEditButton class="mr-1" @click="openEdit(item)" />
        <CustomDeleteButton
               :disabled="item.id === auth.user?.id" @click="removeUser(item)" />
      </template>
      <template #no-data>
        <div class="pa-6 text-grey">Пользователи не найдены</div>
      </template>
    </v-data-table>

    <!-- Диалог создания / редактирования -->
    <v-dialog v-model="dialog" max-width="520" persistent>
      <v-card :title="editing ? 'Редактировать пользователя' : 'Новый пользователь'">
        <v-card-text>
          <div class="form-field mb-3">
            <div class="field-label">Логин</div>
            <v-text-field v-model="form.username" variant="solo" density="compact" flat hide-details
                          :disabled="!!editing" placeholder="napr. ivanov" />
          </div>
          <div class="form-field mb-3">
            <div class="field-label">Сотрудник (ФИО)</div>
            <v-autocomplete
              v-model="selectedEmployeeId"
              :items="allEmployees"
              item-title="full_name"
              item-value="id"
              variant="solo"
              density="compact"
              flat
              hide-details="auto"
              clearable
              :filter="employeeFilter"
              :loading="employeesLoading"
              placeholder="Начните вводить ФИО для поиска..."
              prepend-inner-icon="mdi-magnify"
              @update:model-value="onEmployeeSelected"
              @update:search="onEmployeeSearch"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <span style="font-weight: 500;">{{ item.raw.full_name }}</span>
                  </template>
                  <template #append>
                    <span v-if="item.raw.tab_number" style="font-size: 0.8rem; color: #666;">
                      Таб. {{ item.raw.tab_number }}
                    </span>
                  </template>
                </v-list-item>
              </template>
              <template #no-data>
                <v-list-item title="Сотрудник не найден. Добавьте сотрудника в справочник." />
              </template>
            </v-autocomplete>
          </div>
          <div class="form-field mb-3">
            <div class="field-label">{{ editing ? 'Новый пароль (оставьте пустым, чтобы не менять)' : 'Пароль' }}</div>
            <v-text-field v-model="form.password" type="password" variant="solo" density="compact" flat hide-details
                          autocomplete="new-password" placeholder="Минимум 4 символа" />
          </div>

          <!-- ✅ ЭТАП 8: основная роль (заменяет старые чекбоксы is_admin/is_hr/...) -->
          <div class="field-label mb-1">Основная роль</div>
          <v-select :menu-icon="null" v-model="form.role" :items="roleOptions" density="compact" variant="outlined" hide-details
                    item-title="title" item-value="value" class="mb-3">
            <!-- ✅ ЭТАП 6/8: кнопка «Применить рекомендуемые права для этой роли» -->
            <template #append>
              <v-btn icon="mdi-refresh" size="small" variant="text"
                     title="Применить рекомендуемые права для этой роли"
                     @click="applyRolePermissions" />
            </template>
          </v-select>

          <!-- Доступ к вкладкам сайта (права из новой системы permissions) -->
          <div class="mb-3">
            <div class="field-label mb-1">Доступ к вкладкам сайта</div>
            <v-alert v-if="form.role === 'admin'" type="info" variant="tonal" density="compact" class="mb-2">
              Администратор имеет автоматический доступ ко всем вкладкам
            </v-alert>
            <template v-else>
              <v-checkbox v-model="form.allTabs" label="Все вкладки (по умолчанию)" density="compact" hide-details color="#2d5a3d" class="mb-1" />
              <div v-if="!form.allTabs" class="d-flex flex-column pl-6" style="gap: 2px;">
                <v-checkbox v-for="tab in tabOptions" :key="tab.value" v-model="form.permissions"
                            :value="tab.value" :label="tab.title" density="compact" hide-details color="#2d5a3d" />
              </div>
              <div class="text-caption text-grey mt-1">
                Если выбраны конкретные вкладки — в меню пользователю будут показаны только они;
                вход по прямой ссылке на закрытую вкладку приведёт к переходу на первую доступную страницу.
              </div>
            </template>
          </div>

          <!-- ✅ ЭТАП 8: новая система прав — единственный источник настроек (старые чекбоксы удалены) -->
          <v-divider class="my-4" />
          <div class="field-label mb-1">🛡️ Настройки прав доступа</div>

          <div class="d-flex" style="gap: 8px;">
            <v-select :menu-icon="null" v-model="form.data_scope" :items="dataScopeOptions" density="compact" variant="outlined" hide-details
                      clearable label="Область видимости данных" item-title="title" item-value="value" class="flex-grow-1 mb-3" />
          </div>

          <!-- Права на подразделения: единый блок при области видимости «Выбранные подразделения» -->
          <template v-if="form.data_scope === 'custom' && form.role !== 'admin'">
            <v-checkbox v-model="allDepartments" label="Все подразделения" density="compact" hide-details color="blue-grey" class="mb-2" />
            <v-select v-if="!allDepartments" :menu-icon="null" v-model="form.allowed_department_ids" :items="deptItems"
                      multiple chips closable-chips density="compact" variant="outlined" hide-details clearable
                      label="Выберите подразделения" item-title="title" item-value="value" class="mb-2" />
            <div class="text-caption text-grey mb-3">Если не выбрано ни одного подразделения — сотрудник будет недоступен в списке при создании табеля.</div>
          </template>

          <!-- ✅ ЭТАП 6: визуальная индикация автозаполнения прав -->
          <v-alert v-if="showAutoFillAlert" type="success" density="compact" variant="tonal" class="mb-3" closable
                   @click:close="showAutoFillAlert = false">
            ✅ Специальные права автоматически настроены для роли "{{ form.role }}"
          </v-alert>

          <div class="field-label mb-1">Специальные возможности:</div>
          <div class="d-flex flex-column" style="gap: 2px;">
            <v-checkbox v-model="form.can_approve" label="Согласовывать табели" density="compact" hide-details color="#2d5a3d" />
            <v-checkbox v-model="form.can_edit_references" label="Редактировать справочники" density="compact" hide-details color="#2d5a3d" />
            <v-checkbox v-model="form.can_view_salary" label="Видеть зарплатные данные (часы по тарифу)" density="compact" hide-details color="#2d5a3d" />
            <v-checkbox v-model="form.can_import" label="Импортировать данные" density="compact" hide-details color="#2d5a3d" />
            <v-checkbox v-model="form.can_manage_users" label="Управлять пользователями" density="compact" hide-details color="#2d5a3d" />
            <v-checkbox v-model="form.can_view_all_tabels" label="Просмотр всех табелей (без редактирования)" density="compact" hide-details color="warning" />
          </div>

          <v-alert v-if="dialogError" type="error" density="compact" variant="tonal" class="mt-3">{{ dialogError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">Отмена</v-btn>
          <v-btn color="#2d5a3d" :loading="saving" @click="saveUser">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref, watch, nextTick } from 'vue'
import api from '../api'
import CustomEditButton from '../components/CustomEditButton.vue'
import CustomDeleteButton from '../components/CustomDeleteButton.vue'
import { auth } from '../auth'

const headers = [
  { title: 'Логин', key: 'username', sortable: true },
  { title: 'ФИО', key: 'full_name', sortable: true },
  { title: 'Роли', key: 'roles', sortable: false },
  { title: 'Подразделения', key: 'departments', sortable: false },
  { title: '', key: 'actions', sortable: false }
]

const users = ref([])
const loading = ref(false)
const error = ref('')

const dialog = ref(false)
const saving = ref(false)
const dialogError = ref('')
const editing = ref(null)
const allDepartments = ref(false)
const deptItems = ref([])

// ✅ Доступ к вкладкам сайта: ключ = путь страницы (совпадает с ALLOWED_PAGE_KEYS на бэкенде)
const tabOptions = [
  { title: 'Сводка', value: '/' },
  { title: 'Табель', value: '/tabels' },
  { title: 'Сотрудники', value: '/employees' },
  { title: 'Импорт', value: '/import' },
  { title: 'Расчёт событий', value: '/turnstile-fix' },
  { title: 'Табель фактический', value: '/timesheet-report' },
  { title: 'Отчёт по часам', value: '/hours-report' },
  { title: 'Подразделения', value: '/departments' },
  { title: 'Графики', value: '/schedules' },
  { title: 'Настройки', value: '/settings' },
  { title: 'Увольнительные записки', value: '/dismissal-notes' },
  { title: 'Документы', value: '/documents' },
  { title: 'Пользователи', value: '/users' }
]

// ✅ ЭТАП 5: варианты для новой системы прав (role / data_scope)
const roleOptions = [
  { title: 'Пользователь (Только свои)', value: 'user' },
  { title: 'Начальник участка', value: 'manager' },
  { title: 'Кадровик', value: 'hr' },
  { title: 'Инспектор табелей', value: 'inspector' },
  { title: 'Бухгалтер', value: 'accountant' },
  { title: 'Администратор', value: 'admin' }
]

// ✅ ЭТАП 8: отображение роли в таблице пользователей (только новая система)
const ROLE_TITLES = Object.fromEntries(roleOptions.map(r => [r.value, r.title]))
const ROLE_COLORS = { admin: 'deep-purple', hr: 'teal', manager: 'blue', inspector: 'orange', accountant: 'indigo', user: 'blue-grey' }
const roleTitle = role => ROLE_TITLES[role] || role
const roleChipColor = role => ROLE_COLORS[role] || 'grey'

const dataScopeOptions = [
  { title: 'Только свои табели', value: 'own' },
  { title: 'Своё подразделение', value: 'department' },
  { title: 'Выбранные подразделения', value: 'custom' },
  { title: 'Все подразделения', value: 'all' }
]

// ✅ ЭТАП 6: Рекомендуемые настройки специальных прав для каждой роли
const ROLE_PERMISSIONS = {
  admin: {
    can_approve: true, can_edit_references: true, can_view_salary: true,
    can_import: true, can_manage_users: true, can_view_all_tabels: true
  },
  hr: {
    can_approve: true, can_edit_references: true, can_view_salary: true,
    can_import: true, can_manage_users: false, can_view_all_tabels: true
  },
  manager: {
    can_approve: true, can_edit_references: false, can_view_salary: false,
    can_import: false, can_manage_users: false, can_view_all_tabels: false
  },
  inspector: {
    can_approve: false, can_edit_references: false, can_view_salary: false,
    can_import: false, can_manage_users: false, can_view_all_tabels: true // Только просмотр
  },
  accountant: {
    can_approve: false, can_edit_references: false, can_view_salary: true, // Бухгалтеру нужны зарплатные данные
    can_import: false, can_manage_users: false, can_view_all_tabels: true
  },
  user: {
    can_approve: false, can_edit_references: false, can_view_salary: false,
    can_import: false, can_manage_users: false, can_view_all_tabels: false
  }
}

// ✅ ЭТАП 8 (шаг 3): Рекомендуемый доступ к вкладкам (permissions) для каждой роли.
// null / [] => «все вкладки» (allTabs = true).
const ROLE_TAB_PERMISSIONS = {
  admin: null,                                     // доступ ко всем вкладкам по роли
  hr: ['/', '/tabels', '/employees', '/turnstile-fix', '/timesheet-report', '/hours-report', '/dismissal-notes', '/documents'],
  manager: ['/tabels', '/timesheet-report'],
  inspector: ['/tabels', '/timesheet-report', '/hours-report'],
  accountant: ['/tabels', '/hours-report', '/timesheet-report'],
  user: ['/tabels']
}

const CAN_KEYS = ['can_approve', 'can_edit_references', 'can_view_salary', 'can_import', 'can_manage_users', 'can_view_all_tabels']

const emptyForm = () => ({
  username: '', full_name: '', password: '',
  allTabs: true, permissions: [],
  // ✅ ЭТАП 8: форма использует ТОЛЬКО новую систему прав (role, data_scope, can_*, permissions).
  // Старые булевы поля (is_admin, is_hr, timesheet_inspector, is_user, is_report,
  // is_documents_manager) и deptIds удалены из модели формы и не отправляются на бэкенд.
  role: 'user', data_scope: 'own', allowed_department_ids: [],
  can_approve: false, can_edit_references: false, can_view_salary: false,
  can_import: false, can_manage_users: false, can_view_all_tabels: false
})
const form = ref(emptyForm())

// Служебные флаги: автозаполнение не должно срабатывать при открытии формы на редактирование
let suppressRoleWatch = false
let autoFillHideTimer = null
const showAutoFillAlert = ref(false)

// ✅ ЭТАП 8 (шаг 3): Применить рекомендуемые права текущей роли к форме:
// специальные can_* флаги И доступ к вкладкам (permissions/allTabs).
function applyRolePermissions() {
  const perms = ROLE_PERMISSIONS[form.value.role] || ROLE_PERMISSIONS.user
  for (const key of CAN_KEYS) form.value[key] = !!perms[key]
  // ✅ ЭТАП 8: автоинициализация permissions по роли
  // (admin — все вкладки/null, user — ['/tabels'] и т.д.)
  const tabs = ROLE_TAB_PERMISSIONS[form.value.role] ?? null
  if (tabs === null || tabs.length === 0) {
    form.value.allTabs = true
    form.value.permissions = []
  } else {
    form.value.allTabs = false
    form.value.permissions = tabs.slice()
  }
  // Визуальная обратная связь — показать alert и скрыть через 5 секунд
  showAutoFillAlert.value = true
  clearTimeout(autoFillHideTimer)
  autoFillHideTimer = setTimeout(() => { showAutoFillAlert.value = false }, 5000)
}

// Watcher на роль — автоматически проставляет специальные права при ЯВНОМ изменении роли.
// При загрузке существующего пользователя (openEdit) срабатывание подавляется,
// чтобы не затирать права, сохранённые ранее; после этого админ может менять галочки вручную.
// ВАЖНО: объявлен ПОСЛЕ const form (исправление "Cannot access 'form' before initialization").
watch(() => form.value.role, (newRole, oldRole) => {
  if (suppressRoleWatch) return
  if (!newRole || newRole === oldRole) return
  applyRolePermissions()
})

// ✅ Выбор сотрудника из справочника вместо ручного ввода ФИО
const allEmployees = ref([])
const employeesLoaded = ref(false)
const employeesLoading = ref(false)
const selectedEmployeeId = ref(null)
let employeeSearchTimer = null

// Нормализация для поиска (нижний регистр + Ё->Е)
const normSearch = s => String(s ?? '').toLowerCase().replace(/ё/g, 'е')

async function loadEmployees() {
  if (employeesLoaded.value) return
  employeesLoading.value = true
  try {
    const { data } = await api.get('/employees/', { params: { limit: 3000 } })
    allEmployees.value = Array.isArray(data) ? data : []
    employeesLoaded.value = true
  } catch (e) {
    console.error('Ошибка загрузки сотрудников:', e)
    allEmployees.value = []
  } finally {
    employeesLoading.value = false
  }
}

// Поиск по подстроке (ФИО / табельный номер / подразделение) с нормализацией Ё->Е, максимум 50 совпадений
const employeeFilter = (items, query) => {
  if (!query || !query.trim()) return items.slice(0, 50)
  const q = normSearch(query)
  return items.filter(e =>
    normSearch(e.full_name).includes(q) ||
    normSearch(String(e.tab_number ?? '')).includes(q) ||
    normSearch(e.department_name || '').includes(q)
  ).slice(0, 50)
}

// Обработчик поиска: при необходимости дозагружает справочник сотрудников (сам поиск — локальный, debounce в v-autocomplete встроен)
function onEmployeeSearch(query) {
  clearTimeout(employeeSearchTimer)
  if (!query || query.trim().length < 2) return
  employeeSearchTimer = setTimeout(() => {
    if (!employeesLoaded.value) loadEmployees()
  }, 300)
}

// При выборе сотрудника автоматически заполняем поля формы
function onEmployeeSelected(employeeId) {
  if (!employeeId) {
    // Сброс выбора — ФИО очищается, сохранить форму без выбранного сотрудника нельзя
    form.value.full_name = ''
    form.value.tab_number = ''
    form.value.position = ''
    form.value.department_id = null
    return
  }
  const emp = allEmployees.value.find(e => e.id === employeeId)
  if (emp) {
    form.value.full_name = emp.full_name
    form.value.tab_number = emp.tab_number || ''
    form.value.position = emp.position || ''
    form.value.department_id = emp.department_id || null
  }
}

// Попытаться найти пользователя среди сотрудников (по ФИО или таб. номеру) и выбрать его заранее
function preselectEmployee(fullName) {
  selectedEmployeeId.value = null
  if (!fullName) return
  const norm = normSearch(fullName)
  const emp = allEmployees.value.find(e => normSearch(e.full_name) === norm)
  if (emp) {
    selectedEmployeeId.value = emp.id
    form.value.full_name = emp.full_name
    form.value.tab_number = emp.tab_number || ''
    form.value.position = emp.position || ''
    form.value.department_id = emp.department_id || null
  }
}

async function loadDepartments() {
  try {
    // полный список доступен только администратору (этот экран и так только для него)
    const { data } = await api.get('/departments/?flat=true&all=true')
    deptItems.value = data.map(d => ({ title: d.parent_name ? `${d.name} (${d.parent_name})` : d.name, value: d.id }))
  } catch (e) { /* справочник под разделением не критичен */ }
}

function parseAllowed(raw) {
  if (!raw) return []
  const s = String(raw).trim()
  if (s === '*') return []
  try {
    const arr = JSON.parse(s)
    return Array.isArray(arr) ? arr.map(Number).filter(n => !Number.isNaN(n)) : []
  } catch (e) { return [] }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/users/with-roles')
    users.value = data
  } catch (e) {
    if (e.response?.status === 401) auth.logout()
    else if (e.response?.status === 403) error.value = 'Справочник пользователей доступен только Администратору.'
    else error.value = e.response?.data?.detail || 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  dialogError.value = ''
  allDepartments.value = false
  form.value = emptyForm()
  selectedEmployeeId.value = null
  loadDepartments()
  loadEmployees()
  dialog.value = true
}

function openEdit(item) {
  editing.value = item
  dialogError.value = ''
  // ✅ ЭТАП 6: подавляем watcher на роль, чтобы загрузка сохранённых прав не затиралась автозаполнением
  suppressRoleWatch = true
  const perms = Array.isArray(item.permissions) ? item.permissions.slice() : null
  form.value = {
    username: item.username,
    full_name: item.full_name,
    password: '',
    // ✅ null/пусто — все вкладки; список — только выбранные
    allTabs: !perms || perms.length === 0,
    permissions: perms || [],
    // ✅ ЭТАП 8: заполняем ТОЛЬКО новые поля из ответа API (с безопасными значениями по умолчанию).
    // Старые булевы поля (is_admin/is_hr/...) в форму больше не попадают.
    role: item.role || 'user',
    data_scope: item.data_scope || 'own',
    allowed_department_ids: Array.isArray(item.allowed_department_ids) && item.allowed_department_ids.length
      ? item.allowed_department_ids.slice()
      : parseAllowed(item.allowed_departments), // тихий фолбэк для старых данных
    can_approve: !!item.can_approve,
    can_edit_references: !!item.can_edit_references,
    can_view_salary: !!item.can_view_salary,
    can_import: !!item.can_import,
    can_manage_users: !!item.can_manage_users,
    can_view_all_tabels: !!item.can_view_all_tabels,
  }
  allDepartments.value = !!item.all_departments
  loadDepartments()
  dialog.value = true
  // ✅ Загружаем сотрудников и пытаемся найти соответствие (по ФИО) для предварительного выбора
  loadEmployees().then(() => preselectEmployee(item.full_name))
  // Разрешаем watcher'у снова работать после того, как форма заполнена сохранёнными значениями
  nextTick(() => { suppressRoleWatch = false })
}

async function saveUser() {
  // Валидация: ФИО должно быть выбрано из списка сотрудников (ручной ввод убран)
  if (!form.value.full_name || !form.value.full_name.trim()) {
    dialogError.value = 'Выберите сотрудника из списка'
    return
  }
  saving.value = true
  dialogError.value = ''
  try {
    // ✅ ЭТАП 8: подразделения берутся из нового поля allowed_department_ids
    const deptIds = form.value.allowed_department_ids || []
    const allowed = allDepartments.value ? '*' : JSON.stringify(deptIds)
    // ✅ Права к вкладкам: админ по роли или «все вкладки» -> null, иначе — выбранный список
    const permissions = (form.value.role !== 'admin' && !form.value.allTabs)
      ? (form.value.permissions || [])
      : null
    // ✅ ЭТАП 8: payload содержит ТОЛЬКО новую систему прав — старые поля не отправляются
    const basePayload = {
      full_name: form.value.full_name,
      allowed_departments: allowed,
      permissions,
      role: form.value.role,
      data_scope: form.value.data_scope,
      allowed_department_ids: deptIds,
      can_approve: form.value.can_approve,
      can_edit_references: form.value.can_edit_references,
      can_view_salary: form.value.can_view_salary,
      can_import: form.value.can_import,
      can_manage_users: form.value.can_manage_users,
      can_view_all_tabels: form.value.can_view_all_tabels
    }
    if (editing.value) {
      const payload = { ...basePayload, username: undefined }
      if (!form.value.password) delete payload.password
      else payload.password = form.value.password
      await api.put(`/users/with-roles/${editing.value.id}`, payload)
    } else {
      const payload = { ...basePayload, username: form.value.username, password: form.value.password }
      await api.post('/users/with-roles', payload)
    }
    dialog.value = false
    await load()
    // Если меняли права текущего пользователя — обновляем его данные с сервера
    if (editing.value && editing.value.id === auth.user?.id) await auth.refresh()
  } catch (e) {
    const d = e.response?.data?.detail
    dialogError.value = typeof d === 'string' ? d : 'Ошибка сохранения'
  } finally {
    saving.value = false
  }
}

async function removeUser(item) {
  if (!confirm(`Удалить пользователя «${item.username}»?`)) return
  try {
    await api.delete(`/users/with-roles/${item.id}`)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка удаления'
  }
}

onMounted(load)
</script>

<style scoped>
.form-field .field-label,
.field-label {
  font-size: 12px;
  color: rgba(0, 0, 0, .6);
  margin-bottom: 2px;
}
</style>
