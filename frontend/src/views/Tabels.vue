<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h2 class="text-h5" style="font-weight:bold;">
        Табели
        <v-chip v-if="auth.isTimesheetInspector" size="small" class="ml-2">Инспектор табелей — видны все</v-chip>
        <v-chip v-else size="small" class="ml-2" color="grey">Видны только мои табели</v-chip>
      </h2>
      <v-spacer />
      <v-select
        :menu-icon="null"
        v-model="filterMonth"
        :items="monthItems"
        item-title="title"
        item-value="value"
        label="Месяц"
        clearable
        density="compact"
        hide-details
        variant="outlined"
        style="max-width: 170px;"
        class="mr-2"
      />
      <v-select
        :menu-icon="null"
        v-model="filterYear"
        :items="years"
        label="Год"
        clearable
        density="compact"
        hide-details
        variant="outlined"
        style="max-width: 120px;"
        class="mr-4"
      />
      <v-btn
        v-if="auth.isTimesheetInspector"
        color="#2d5a3d"
        prepend-icon="mdi-plus"
        @click="openCreate"
      >
        Создать табель
      </v-btn>
    </div>

    <v-data-table
      :headers="headers"
      :items="tabels"
      :loading="loading"
      hover
      class="rounded-lg"
      @click:row="openTabel"
    >
      <template #item.period="{ item }">
        {{ monthNames[item.month - 1] }} {{ item.year }}
      </template>
      <template #item.actions="{ item }">
        <v-btn size="small" variant="text" color="#2d5a3d" prepend-icon="mdi-open-in-new"
               @click.stop="openTabel(item)">
          Открыть
        </v-btn>
        <v-btn v-if="auth.isTimesheetInspector" size="small" variant="text" color="red"
               icon="mdi-delete" @click.stop="removeTabel(item)" />
      </template>
      <template #no-data>
        <div class="pa-6 text-grey">Табели не найдены</div>
      </template>
    </v-data-table>

    <!-- Диалог создания табеля -->
    <v-dialog v-model="createDialog" max-width="480">
      <v-card title="Новый табель">
        <v-card-text>
          <div class="form-field mb-3">
            <div class="field-label">Месяц</div>
            <v-select :menu-icon="null" v-model="form.month" :items="monthItems" item-title="title" item-value="value"
                      variant="solo" density="compact" flat hide-details />
          </div>
          <div class="form-field mb-3">
            <div class="field-label">Год</div>
            <v-select :menu-icon="null" v-model="form.year" :items="years" variant="solo" density="compact" flat hide-details />
          </div>
          <div class="form-field mb-3">
            <div class="field-label">Подразделение</div>
            <v-select :menu-icon="null" v-model="form.department_id" :items="departments" item-title="name" item-value="id"
                      variant="solo" density="compact" flat clearable hide-details />
          </div>
          <div class="form-field">
            <div class="field-label">Ответственный</div>
            <v-select :menu-icon="null" v-model="form.responsible_user_id" :items="users" item-title="label" item-value="id"
                      variant="solo" density="compact" flat hide-details />
          </div>
          <v-alert v-if="createError" type="error" density="compact" class="mt-2" variant="tonal">{{ createError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="createDialog = false">Отмена</v-btn>
          <v-btn color="#2d5a3d" :loading="creating" @click="createTabel">Создать</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { auth } from '../auth'

const router = useRouter()
const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

const headers = [
  { title: 'Период', key: 'period', sortable: true },
  { title: 'Подразделение', key: 'department_name', sortable: true },
  { title: 'Ответственный', key: 'responsible_user_name' },
  { title: 'Сотрудников', key: 'employees_count' },
  { title: '', key: 'actions', sortable: false }
]

const tabels = ref([])
const loading = ref(false)
const filterMonth = ref(null)
const filterYear = ref(new Date().getFullYear())

const now = new Date()
const years = Array.from({ length: 6 }, (_, i) => now.getFullYear() - 3 + i)
const monthItems = monthNames.map((title, idx) => ({ title, value: idx + 1 }))

const createDialog = ref(false)
const creating = ref(false)
const createError = ref('')
const departments = ref([])
const users = ref([])
const form = ref({ month: now.getMonth() + 1, year: now.getFullYear(), department_id: null, responsible_user_id: null })

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filterMonth.value) params.month = filterMonth.value
    if (filterYear.value) params.year = filterYear.value
    const { data } = await api.get('/tabels/', { params })
    tabels.value = data
  } catch (e) {
    if (e.response?.status === 401) auth.logout()
  } finally {
    loading.value = false
  }
}

function openTabel(e, item) {
  const row = item || e
  router.push(`/tabels/${row.id}`)
}

async function removeTabel(item) {
  if (!confirm(`Удалить табель за ${monthNames[item.month - 1]} ${item.year}?`)) return
  try {
    await api.delete(`/tabels/${item.id}`)
    load()
  } catch (e) {
    alert(e.response?.data?.detail || 'Ошибка удаления')
  }
}

async function openCreate() {
  createError.value = ''
  createDialog.value = true
  try {
    departments.value = (await api.get('/departments/')).data
    users.value = (await api.get('/auth/users')).data.map(u => ({
      id: u.id, label: `${u.full_name || u.username} (${u.username})`
    }))
    form.value.responsible_user_id = auth.user?.id
  } catch (e) { /* ignore */ }
}

async function createTabel() {
  creating.value = true
  createError.value = ''
  try {
    const { data } = await api.post('/tabels/', form.value)
    createDialog.value = false
    router.push(`/tabels/${data.id}`)
  } catch (e) {
    createError.value = e.response?.data?.detail || 'Ошибка создания'
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.form-field .field-label {
  font-size: 12px;
  color: rgba(0,0,0,.6);
  margin-bottom: 2px;
}
</style>
