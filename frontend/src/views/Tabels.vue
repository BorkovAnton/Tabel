<template>
  <div>
    <v-card class="pa-4 mb-4" flat>
      <div class="d-flex align-center mb-4">
        <h2 class="text-h5" style="font-weight:bold;">
          Табели
          <v-chip v-if="auth.isTimesheetInspector" size="small" class="ml-2">Инспектор табелей — видны все</v-chip>
          <v-chip v-else size="small" class="ml-2" color="grey">Видны только мои табели</v-chip>
        </h2>
      </div>

      <v-row class="mb-4">
        <v-col cols="12" md="3">
          <v-select
            v-model="filterMonth"
            :items="monthItems"
            item-title="title"
            item-value="value"
            label="Месяц"
            clearable
            density="compact"
            hide-details
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filterYear"
            :items="years"
            label="Год"
            clearable
            density="compact"
            hide-details
            variant="outlined"
          />
        </v-col>
      </v-row>

      <v-btn
        v-if="auth.canManageTabels"
        color="#2d5a3d"
        prepend-icon="mdi-plus"
        class="mt-4"
        @click="openCreate"
      >
        Создать табель
      </v-btn>
    </v-card>

    <v-data-table
      :headers="headers"
      :items="tabels"
      :loading="loading"
      hover
      class="rounded-lg"
      return-object
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
        <v-btn v-if="auth.canManageTabels"
               size="small" variant="text" color="#2d5a3d"
               title="Копировать табель на новый месяц" @click.stop="openCopyDialog(item)">
          <template #prepend><CustomCopyButton /></template>
        </v-btn>
        <v-btn v-if="canDelete(item)"
               size="small" variant="text" color="red"
               title="Удалить табель" @click.stop="removeTabel(item)">
          <template #prepend><CustomDeleteButton /></template>
        </v-btn>
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

    <!-- Диалог копирования табеля на новый месяц -->
    <v-dialog v-model="copyDialog" max-width="500">
      <v-card title="Копировать табель">
        <v-card-text>
          <p class="mb-2">
            Копирование табеля:
            <strong>{{ sourceTabel?.department_name || '—' }}
              ({{ monthNames[(sourceTabel?.month ?? 1) - 1] }} {{ sourceTabel?.year }})</strong>
          </p>
          <p class="text-caption text-grey mb-4">
            Будет создан новый табель с тем же списком сотрудников.
            Ежедневные данные (часы/коды) будут очищены — это новый период.
          </p>
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="newMonth"
                :items="monthItems"
                item-title="title"
                item-value="value"
                label="Новый месяц"
                variant="outlined"
                density="compact"
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="newYear"
                :items="years"
                label="Новый год"
                variant="outlined"
                density="compact"
              />
            </v-col>
          </v-row>
          <v-alert v-if="copyError" type="error" density="compact" variant="tonal">{{ copyError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="copyDialog = false">Отмена</v-btn>
          <v-btn color="#2d5a3d" :loading="copying" @click="executeCopy">Копировать</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import CustomDeleteButton from '../components/CustomDeleteButton.vue'
import CustomCopyButton from '../components/CustomCopyButton.vue'
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
  // В Vuetify 3 без return-object первый аргумент — объект события (без id),
  // второй — данные строки. С return-object первым идёт сама строка.
  const candidates = [item, e, e?.item, e?.item?.raw]
  const row = candidates.find((c) => c && Number.isInteger(Number(c.id)) && Number(c.id) > 0)
  if (!row) {
    console.error('Не удалось определить строку табеля при клике', e, item)
    return
  }
  router.push(`/tabels/${Number(row.id)}`)
}

// Кнопка удаления: инспектор табелей — любой табель; обычный пользователь — только свой.
// id приводим к числу, чтобы избежать несовпадения типов (строка/число).
function canDelete(item) {
  if (!auth.canManageTabels) return false
  if (auth.isTimesheetInspector || auth.isAdmin) return true
  return Number(item.responsible_user_id) === Number(auth.user?.id)
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
    await auth.refresh()  // подтянуть актуальные права на подразделения
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

// ─── Копирование табеля на новый месяц ───
const copyDialog = ref(false)
const sourceTabel = ref(null)
const newMonth = ref(now.getMonth() + 1)
const newYear = ref(now.getFullYear())
const copying = ref(false)
const copyError = ref('')

function openCopyDialog(tabel) {
  sourceTabel.value = tabel
  copyError.value = ''
  // По умолчанию предлагаем следующий месяц после исходного периода
  let nextM = tabel.month + 1
  let nextY = tabel.year
  if (nextM > 12) {
    nextM = 1
    nextY += 1
  }
  newMonth.value = nextM
  newYear.value = nextY
  copyDialog.value = true
}

async function executeCopy() {
  if (!sourceTabel.value) return
  copying.value = true
  copyError.value = ''
  try {
    const { data } = await api.post('/tabels/copy', {
      source_id: sourceTabel.value.id,
      new_month: newMonth.value,
      new_year: newYear.value,
    })
    copyDialog.value = false
    await load()          // обновляем список без перезагрузки страницы
    router.push(`/tabels/${data.id}`)  // открываем скопированный табель
  } catch (e) {
    console.error(e)
    copyError.value = e.response?.data?.detail || 'Ошибка при копировании табеля'
  } finally {
    copying.value = false
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
