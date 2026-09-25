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
        <v-chip v-if="item.is_user" size="x-small" color="blue" variant="toned">Пользователь</v-chip>
        <span v-if="!item.is_admin && !item.is_hr && !item.timesheet_inspector && !item.is_user" class="text-grey text-caption">—</span>
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
        <v-btn size="small" variant="text" icon="mdi-pencil" color="#2d5a3d" @click="openEdit(item)" />
        <v-btn size="small" variant="text" icon="mdi-delete" color="red"
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
            <div class="field-label">ФИО</div>
            <v-text-field v-model="form.full_name" variant="solo" density="compact" flat hide-details
                          placeholder="Иванов Иван Иванович" />
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
          </div>

          <div v-if="form.is_user && !form.is_admin && !form.is_hr && !form.timesheet_inspector" class="mt-3">
            <div class="field-label mb-1">Права на подразделения</div>
            <v-checkbox v-model="allDepartments" label="Все подразделения" density="compact" hide-details color="blue-grey" class="mb-1" />
            <v-select :menu-icon="null" v-if="!allDepartments" v-model="form.deptIds" :items="deptItems" multiple chips closable-chips
                      density="compact" variant="outlined" hide-details clearable label="Выберите подразделения"
                      item-title="title" item-value="value" />
            <div class="text-caption text-grey mt-1">Если не выбрано ни одного подразделения — сотрудник будет недоступен в списке при создании табеля.</div>
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
import { onMounted, ref } from 'vue'
import api from '../api'
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
const form = ref({ username: '', full_name: '', password: '', is_admin: false, is_hr: false, timesheet_inspector: false, is_user: true, deptIds: [] })

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
  form.value = { username: '', full_name: '', password: '', is_admin: false, is_hr: false, timesheet_inspector: false, is_user: true, deptIds: [] }
  loadDepartments()
  dialog.value = true
}

function openEdit(item) {
  editing.value = item
  dialogError.value = ''
  form.value = {
    username: item.username,
    full_name: item.full_name,
    password: '',
    is_admin: item.is_admin,
    is_hr: item.is_hr,
    timesheet_inspector: item.timesheet_inspector,
    is_user: item.is_user !== false,
    deptIds: parseAllowed(item.allowed_departments),
  }
  allDepartments.value = !!item.all_departments
  loadDepartments()
  dialog.value = true
}

async function saveUser() {
  saving.value = true
  dialogError.value = ''
  try {
    const allowed = allDepartments.value ? '*' : JSON.stringify(form.value.deptIds || [])
    if (editing.value) {
      const payload = { ...form.value, allowed_departments: allowed }
      if (!payload.password) delete payload.password
      payload.username = undefined
      delete payload.deptIds
      await api.put(`/users/with-roles/${editing.value.id}`, payload)
    } else {
      const payload = { ...form.value, allowed_departments: allowed }
      delete payload.deptIds
      await api.post('/users/with-roles', payload)
    }
    dialog.value = false
    await load()
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
