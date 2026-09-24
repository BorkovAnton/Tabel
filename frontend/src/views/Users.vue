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
        <v-chip v-if="item.timesheet_inspector" size="x-small" color="orange" variant="toned">Инспектор табелей</v-chip>
        <span v-if="!item.is_admin && !item.is_hr && !item.timesheet_inspector" class="text-grey text-caption">—</span>
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
  { title: '', key: 'actions', sortable: false }
]

const users = ref([])
const loading = ref(false)
const error = ref('')

const dialog = ref(false)
const saving = ref(false)
const dialogError = ref('')
const editing = ref(null)
const form = ref({ username: '', full_name: '', password: '', is_admin: false, is_hr: false, timesheet_inspector: false })

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
  form.value = { username: '', full_name: '', password: '', is_admin: false, is_hr: false, timesheet_inspector: false }
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
  }
  dialog.value = true
}

async function saveUser() {
  saving.value = true
  dialogError.value = ''
  try {
    if (editing.value) {
      const payload = { ...form.value }
      if (!payload.password) delete payload.password
      payload.username = undefined
      await api.put(`/auth/users/${editing.value.id}`, payload)
    } else {
      await api.post('/users/with-roles', form.value)
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
