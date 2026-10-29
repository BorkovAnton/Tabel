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
        <v-chip v-if="item.is_admin" size="x-small" color="deep-purple" variant="toned" class="mr-1">Администратор</v-chip>
        <v-chip v-if="item.is_hr" size="x-small" color="teal" variant="toned" class="mr-1">Кадровик</v-chip>
        <v-chip v-if="item.timesheet_inspector" size="x-small" color="orange" variant="toned" class="mr-1">Инспектор табелей</v-chip>
        <v-chip v-if="item.is_user" size="x-small" color="blue" variant="toned" class="mr-1">Пользователь</v-chip>
        <v-chip v-if="item.is_report" size="x-small" color="indigo" variant="toned">Отчёт</v-chip>
        <v-chip v-if="item.is_documents_manager" size="x-small" color="brown" variant="toned">Документы</v-chip>
        <span v-if="!item.is_admin && !item.is_hr && !item.timesheet_inspector && !item.is_user && !item.is_report && !item.is_documents_manager" class="text-grey text-caption">—</span>
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

          <div class="field-label mb-1">Роли</div>
          <div class="d-flex flex-column" style="gap: 2px;">
            <v-checkbox v-model="form.is_admin" label="Администратор" density="compact" hide-details color="deep-purple" />
            <v-checkbox v-model="form.is_hr" label="Кадровик" density="compact" hide-details color="teal" />
            <v-checkbox v-model="form.timesheet_inspector" label="Инспектор табелей" density="compact" hide-details color="orange" />
            <v-checkbox v-model="form.is_user" label="Пользователь" density="compact" hide-details color="blue" hint="Доступ к «Табель фактический», «Табель», создание и заполнение табелей" persistent-hint />
            <v-checkbox v-model="form.is_report" label="Отчёт" density="compact" hide-details color="indigo" hint="Доступ к странице «Отчёт по часам» (табель vs факт, сверхурочные)" persistent-hint />
            <v-checkbox v-model="form.is_documents_manager" label="Документы и приказы" density="compact" hide-details color="brown" hint="Доступ к разделу «Документы и приказы»: ввод отпусков, командировок, больничных для автозаполнения табеля" persistent-hint />
          </div>

          <div v-if="form.is_user && !form.is_admin && !form.is_hr && !form.timesheet_inspector" class="mt-3">
            <div class="field-label mb-1">Права на подразделения</div>
            <v-checkbox v-model="allDepartments" label="Все подразделения" density="compact" hide-details color="blue-grey" class="mb-1" />
            <v-select :menu-icon="null" v-if="!allDepartments" v-model="form.deptIds" :items="deptItems" multiple chips closable-chips
                      density="compact" variant="outlined" hide-details clearable label="Выберите подразделения"
                      item-title="title" item-value="value" />
            <div class="text-caption text-grey mt-1">Если не выбрано ни одного подразделения — сотрудник будет недоступен в списке при создании табеля.</div>
          </div>

          <!-- ✅ НОВОЕ: доступ к вкладкам сайта -->
          <div class="mt-4">
            <div class="field-label mb-1">Доступ к вкладкам сайта</div>
            <v-alert v-if="form.is_admin" type="info" variant="tonal" density="compact" class="mb-2">
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

          <!-- ✅ ЭТАП 5: Расширенные настройки прав (новая система). Старые чекбоксы выше продолжают работать -->
          <v-divider class="my-4" />
          <div class="field-label mb-1">🛡️ Расширенные настройки прав (Новая система)</div>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Эти настройки дополняют старые права. Старые галочки выше продолжают работать.
            Пока новая логика не активирована — поля сохраняются и будут использоваться в следующих этапах.
          </v-alert>

          <div class="d-flex" style="gap: 8px;">
            <v-select :menu-icon="null" v-model="form.role" :items="roleOptions" density="compact" variant="outlined" hide-details
                      clearable label="Основная роль" item-title="title" item-value="value" class="flex-grow-1 mb-3">
              <!-- ✅ ЭТАП 6: кнопка «Применить рекомендуемые права для этой роли» -->
              <template #append>
                <v-btn icon="mdi-refresh" size="small" variant="text"
                       title="Применить рекомендуемые права для этой роли"
                       @click="applyRolePermissions" />
              </template>
            </v-select>
            <v-select :menu-icon="null" v-model="form.data_scope" :items="dataScopeOptions" density="compact" variant="outlined" hide-details
                      clearable label="Область видимости данных" item-title="title" item-value="value" class="flex-grow-1 mb-3" />
          </div>

          <v-select v-if="form.data_scope === 'custom'" :menu-icon="null" v-model="form.allowed_department_ids" :items="deptItems"
                    multiple chips closable-chips density="compact" variant="outlined" hide-details clearable
                    label="Выберите подразделения (расширенные)" item-title="title" item-value="value" class="mb-3" />

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

const CAN_KEYS = ['can_approve', 'can_edit_references', 'can_view_salary', 'can_import', 'can_manage_users', 'can_view_all_tabels']

// Служебные флаги: автозаполнение не должно срабатывать при открытии формы на редактирование
let suppressRoleWatch = false
let autoFillHideTimer = null
const showAutoFillAlert = ref(false)

// Применить рекомендуемые права текущей роли к форме (кнопка mdi-refresh)
function applyRolePermissions() {
  const perms = ROLE_PERMISSIONS[form.value.role] || ROLE_PERMISSIONS.user
  for (const key of CAN_KEYS) form.value[key] = !!perms[key]
  // Визуальная обратная связь — показать alert и скрыть через 5 секунд
  showAutoFillAlert.value = true
  clearTimeout(autoFillHideTimer)
  autoFillHideTimer = setTimeout(() => { showAutoFillAlert.value = false }, 5000)
}

// Watcher на роль — автоматически проставляет специальные права при ЯВНОМ изменении роли.
// При загрузке существующего пользователя (openEdit) срабатывание подавляется,
// чтобы не затирать права, сохранённые ранее; после этого админ может менять галочки вручную.
watch(() => form.value.role, (newRole, oldRole) => {
  if (suppressRoleWatch) return
  if (!newRole || newRole === oldRole) return
  applyRolePermissions()
})

// Ключи новых полей (этапы 1, 3, 4) — используются при загрузке/сохранении формы
const EXT_PERM_KEYS = ['role', 'data_scope', 'allowed_department_ids',
  'can_approve', 'can_edit_references', 'can_view_salary', 'can_import', 'can_manage_users', 'can_view_all_tabels']

const emptyForm = () => ({
  username: '', full_name: '', password: '',
  // Старые поля (остаются для совместимости)
  is_admin: false, is_hr: false, timesheet_inspector: false, is_user: true, is_report: false, is_documents_manager: false,
  deptIds: [], allTabs: true, permissions: [],
  // ✅ ЭТАП 5: новые поля (этапы 1–4)
  role: 'user', data_scope: 'own', allowed_department_ids: [],
  can_approve: false, can_edit_references: false, can_view_salary: false,
  can_import: false, can_manage_users: false, can_view_all_tabels: false
})
const form = ref(emptyForm())

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
    is_admin: item.is_admin,
    is_hr: item.is_hr,
    timesheet_inspector: item.timesheet_inspector,
    is_user: item.is_user !== false,
    is_report: !!item.is_report,
    is_documents_manager: !!item.is_documents_manager,
    deptIds: parseAllowed(item.allowed_departments),
    // ✅ null/пусто — все вкладки; список — только выбранные
    allTabs: !perms || perms.length === 0,
    permissions: perms || [],
    // ✅ ЭТАП 5: новые поля из ответа API (с безопасными значениями по умолчанию)
    role: item.role || 'user',
    data_scope: item.data_scope || 'own',
    allowed_department_ids: Array.isArray(item.allowed_department_ids) ? item.allowed_department_ids.slice() : [],
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
    const allowed = allDepartments.value ? '*' : JSON.stringify(form.value.deptIds || [])
    // ✅ Права к вкладкам: все вкладки -> null (обратная совместимость), иначе — выбранный список
    const permissions = (!form.value.is_admin && !form.value.allTabs)
      ? (form.value.permissions || [])
      : null
    if (editing.value) {
      const payload = { ...form.value, allowed_departments: allowed, permissions }
      if (!payload.password) delete payload.password
      payload.username = undefined
      delete payload.deptIds
      delete payload.allTabs
      delete payload.tab_number
      delete payload.position
      delete payload.department_id
      await api.put(`/users/with-roles/${editing.value.id}`, payload)
    } else {
      const payload = { ...form.value, allowed_departments: allowed, permissions }
      delete payload.deptIds
      delete payload.allTabs
      delete payload.tab_number
      delete payload.position
      delete payload.department_id
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
