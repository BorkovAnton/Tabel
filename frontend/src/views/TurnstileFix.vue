<template>
  <v-container fluid class="pa-6">
    <!-- Заголовок -->
    <h1 class="text-h4 font-weight-bold mb-6">Расчёт и исправление событий проходной</h1>

    <!-- Фильтры -->
    <v-card class="mb-6" elevation="2">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="dateFrom"
              label="Дата начала"
              type="date"
              variant="outlined"
              prepend-inner-icon="mdi-calendar"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="dateTo"
              label="Дата окончания"
              type="date"
              variant="outlined"
              prepend-inner-icon="mdi-calendar"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4" class="d-flex align-end">
            <v-btn
              color="primary"
              size="large"
              class="flex-grow-1"
              @click="loadIssues"
              :loading="loading"
              prepend-icon="mdi-refresh"
            >
              Обновить
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Статистика -->
    <v-row class="mb-6">
      <v-col cols="12" md="3">
        <v-card elevation="2" color="red">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Нераспознанных ФИО</div>
            <div class="text-h3 font-weight-bold">{{ stats.unrecognized }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="orange">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Пропущенных отметок</div>
            <div class="text-h3 font-weight-bold">{{ stats.missing }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="yellow">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Дубликатов</div>
            <div class="text-h3 font-weight-bold">{{ stats.duplicates }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="blue">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Длинных смен</div>
            <div class="text-h3 font-weight-bold">{{ stats.longShifts }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Вкладки -->
    <v-card elevation="2">
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="unrecognized">
          <v-icon start>mdi-account-question</v-icon>
          Нераспознанные ФИО
        </v-tab>
        <v-tab value="missing">
          <v-icon start>mdi-clock-alert</v-icon>
          Пропущенные отметки
        </v-tab>
        <v-tab value="duplicates">
          <v-icon start>mdi-content-duplicate</v-icon>
          Дубликаты
        </v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="activeTab">
          <!-- Вкладка: Нераспознанные ФИО -->
          <v-window-item value="unrecognized">
            <v-data-table
              :headers="unrecognizedHeaders"
              :items="unrecognizedNames"
              :loading="loading"
              class="elevation-1"
            >
              <template v-slot:item.actions="{ item }">
                <v-btn
                  color="primary"
                  size="small"
                  @click="openLinkDialog(item)"
                  prepend-icon="mdi-link"
                >
                  Связать
                </v-btn>
              </template>
            </v-data-table>
          </v-window-item>

          <!-- Вкладка: Пропущенные отметки -->
          <v-window-item value="missing">
            <v-data-table
              :headers="missingHeaders"
              :items="missingEntries"
              :loading="loading"
              class="elevation-1"
            >
              <template v-slot:item.actions="{ item }">
                <v-btn
                  color="success"
                  size="small"
                  @click="openAddEntryDialog(item)"
                  prepend-icon="mdi-plus"
                >
                  Добавить
                </v-btn>
              </template>
            </v-data-table>
          </v-window-item>

          <!-- Вкладка: Дубликаты (с чекбоксами) -->
          <v-window-item value="duplicates">
            <div class="d-flex justify-space-between align-center mb-4">
              <v-btn
                color="error"
                @click="deleteSelected"
                :disabled="selectedDuplicates.length === 0"
                :loading="deleting"
                prepend-icon="mdi-delete"
              >
                Удалить выбранные ({{ selectedDuplicates.length }})
              </v-btn>
              <div class="text-subtitle-2 text-grey">
                Всего дубликатов: {{ duplicates.length }}
              </div>
            </div>

            <v-data-table
              v-model="selectedDuplicates"
              :headers="duplicateHeaders"
              :items="duplicates"
              :loading="loading"
              show-select
              item-value="id"
              class="elevation-1"
            >
              <template v-slot:item.datetime="{ item }">
                {{ formatDate(item.datetime) }}
              </template>
              <template v-slot:item.event_type="{ item }">
                <v-chip :color="item.event_type === 'in' ? 'green' : 'red'" size="small">
                  {{ item.event_type === 'in' ? 'Вход' : 'Выход' }}
                </v-chip>
              </template>
            </v-data-table>
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>

    <!-- Диалог связывания ФИО -->
    <v-dialog v-model="linkDialog" max-width="500">
      <v-card>
        <v-card-title>Связать ФИО с сотрудником</v-card-title>
        <v-card-text>
          <p class="mb-4">
            <strong>{{ selectedName?.raw_name }}</strong>
            ({{ selectedName?.count }} записей)
          </p>
          <v-select
            v-model="selectedEmployeeId"
            :items="employees"
            item-title="full_name"
            item-value="id"
            label="Выберите сотрудника"
            variant="outlined"
          ></v-select>
          <v-checkbox
            v-model="applyToAll"
            label="Применить ко всем записям с этим ФИО"
            color="primary"
          ></v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="linkDialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="linkEmployee" :loading="linking">
            Связать
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог добавления отметки -->
    <v-dialog v-model="addEntryDialog" max-width="500">
      <v-card>
        <v-card-title>Добавить пропущенную отметку</v-card-title>
        <v-card-text>
          <p class="mb-4">
            <strong>{{ selectedMissing?.employee_name }}</strong>
            <br>
            Дата: {{ selectedMissing?.date }}
            <br>
            Проблема: {{ selectedMissing?.issue }}
          </p>
          <v-text-field
            v-model="newEntryDatetime"
            label="Дата и время"
            type="datetime-local"
            variant="outlined"
          ></v-text-field>
          <v-select
            v-model="newEntryType"
            :items="[
              { title: 'Вход', value: 'in' },
              { title: 'Выход', value: 'out' }
            ]"
            item-title="title"
            item-value="value"
            label="Тип отметки"
            variant="outlined"
          ></v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="addEntryDialog = false">Отмена</v-btn>
          <v-btn color="success" @click="addMissingEntry" :loading="adding">
            Добавить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const loading = ref(false)
const linking = ref(false)
const adding = ref(false)
const deleting = ref(false)

const dateFrom = ref(new Date().toISOString().split('T')[0])
const dateTo = ref(new Date().toISOString().split('T')[0])
const activeTab = ref('unrecognized')

const stats = ref({
  unrecognized: 0,
  missing: 0,
  duplicates: 0,
  longShifts: 0
})

const unrecognizedNames = ref([])
const missingEntries = ref([])
const duplicates = ref([])
const employees = ref([])
const selectedDuplicates = ref([]) // ← Новое: выбранные дубликаты

const linkDialog = ref(false)
const addEntryDialog = ref(false)

const selectedName = ref(null)
const selectedMissing = ref(null)
const selectedEmployeeId = ref(null)
const applyToAll = ref(true)
const newEntryDatetime = ref('')
const newEntryType = ref('in')

const unrecognizedHeaders = [
  { title: 'ФИО', key: 'raw_name' },
  { title: 'Количество записей', key: 'count' },
  { title: 'Действия', key: 'actions', sortable: false }
]

const missingHeaders = [
  { title: 'Сотрудник', key: 'employee_name' },
  { title: 'Дата', key: 'date' },
  { title: 'Существующая отметка', key: 'existing_info' },
  { title: 'Проблема', key: 'issue' },
  { title: 'Действия', key: 'actions', sortable: false }
]

const duplicateHeaders = [
  { title: 'ID', key: 'id', width: '80px' },
  { title: 'Сотрудник ID', key: 'employee_id', width: '120px' },
  { title: 'Дата и время', key: 'datetime', width: '180px' },
  { title: 'Тип', key: 'event_type', width: '100px' },
  { title: 'Дубликат ID', key: 'duplicate_of', width: '120px' }
]

async function loadEmployees() {
  try {
    const response = await api.get('/employees/')
    employees.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки сотрудников:', e)
  }
}

async function loadIssues() {
  loading.value = true
  
  try {
    // Загружаем нераспознанные ФИО
    const unrecognizedResponse = await api.get('/api/turnstile-fix/unrecognized-names')
    unrecognizedNames.value = unrecognizedResponse.data
    stats.value.unrecognized = unrecognizedResponse.data.length
    
    // Загружаем пропущенные отметки
    const missingEntryResponse = await api.get('/api/turnstile-fix/issues', {
      params: { date_from: dateFrom.value, date_to: dateTo.value, issue_type: 'missing_entry' }
    })
    const missingExitResponse = await api.get('/api/turnstile-fix/issues', {
      params: { date_from: dateFrom.value, date_to: dateTo.value, issue_type: 'missing_exit' }
    })
    
    const allMissing = [...missingEntryResponse.data, ...missingExitResponse.data]
    
    missingEntries.value = allMissing.map(item => {
      const emp = employees.value.find(e => e.id === item.employee_id)
      // Убираем дубликаты времени через Set и сортируем
      const uniqueTimes = item.existing_time 
        ? [...new Set(item.existing_time.split(' | '))].sort().join(' | ')
        : ''
      
      const existingInfo = uniqueTimes
        ? `${item.existing_type === 'in' ? 'Вход' : 'Выход'}: ${uniqueTimes}`
        : 'Нет данных'
      
      return {
        ...item,
        employee_name: emp?.full_name || `ID: ${item.employee_id}`,
        existing_info: existingInfo
      }
    })
    
    stats.value.missing = allMissing.length
    
    // Загружаем дубликаты
    const duplicateResponse = await api.get('/api/turnstile-fix/issues', {
      params: { date_from: dateFrom.value, date_to: dateTo.value, issue_type: 'duplicate' }
    })
    duplicates.value = duplicateResponse.data
    stats.value.duplicates = duplicateResponse.data.length
    
  } catch (e) {
    console.error('Ошибка загрузки проблем:', e)
  } finally {
    loading.value = false
  }
}

function openLinkDialog(item) {
  selectedName.value = item
  selectedEmployeeId.value = null
  applyToAll.value = true
  linkDialog.value = true
}

async function linkEmployee() {
  if (!selectedEmployeeId.value) {
    alert('Выберите сотрудника')
    return
  }
  
  linking.value = true
  try {
    if (applyToAll.value) {
      await api.patch('/api/turnstile-fix/bulk-link', {
        raw_name: selectedName.value.raw_name,
        employee_id: selectedEmployeeId.value
      })
    } else {
      await api.patch(`/api/turnstile-fix/${selectedName.value.id}/link`, {
        employee_id: selectedEmployeeId.value
      })
    }
    linkDialog.value = false
    await loadIssues()
  } catch (e) {
    console.error('Ошибка связывания:', e)
    alert('Ошибка при связывании')
  } finally {
    linking.value = false
  }
}

function openAddEntryDialog(item) {
  selectedMissing.value = item
  const baseDate = item.date
  const suggestedTime = item.existing_type === 'in' ? '17:00' : '08:00'
  newEntryDatetime.value = `${baseDate}T${suggestedTime}`
  newEntryType.value = item.existing_type === 'in' ? 'out' : 'in'
  addEntryDialog.value = true
}

async function addMissingEntry() {
  if (!newEntryDatetime.value || !newEntryType.value) {
    alert('Заполните все поля')
    return
  }
  
  adding.value = true
  try {
    await api.post('/api/turnstile-fix/fix-missing', {
      employee_id: selectedMissing.value.employee_id,
      datetime: newEntryDatetime.value,
      event_type: newEntryType.value
    })
    addEntryDialog.value = false
    await loadIssues()
  } catch (e) {
    console.error('Ошибка добавления отметки:', e)
    alert('Ошибка при добавлении отметки')
  } finally {
    adding.value = false
  }
}

// ← НОВАЯ ФУНКЦИЯ: Массовое удаление дубликатов
async function deleteSelected() {
  if (selectedDuplicates.value.length === 0) return

  if (!confirm(`Вы уверены, что хотите удалить ${selectedDuplicates.value.length} дубликатов?`)) {
    return
  }

  deleting.value = true
  try {
    const deletePromises = selectedDuplicates.value.map(id =>
      api.delete(`/api/turnstile-fix/${id}`)
    )
    await Promise.all(deletePromises)

    selectedDuplicates.value = [] // Очищаем выбор
    await loadIssues() // Перезагружаем таблицу
  } catch (e) {
    console.error('Ошибка массового удаления:', e)
    alert('Ошибка при удалении дубликатов')
  } finally {
    deleting.value = false
  }
}

// ← НОВАЯ ФУНКЦИЯ: Форматирование даты
function formatDate(datetime) {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  loadEmployees()
  loadIssues()
})
</script>

<style>
/* Глобальные стили для чекбоксов в таблице */

/* Основной контейнер чекбокса */
.v-data-table .v-checkbox-btn {
  opacity: 1 !important;
}

/* Рамка чекбокса */
.v-data-table .v-checkbox-btn .v-selection-control__wrapper {
  border: 2px solid #2e7d32 !important;
  border-radius: 4px !important;
  background-color: white !important;
}

/* Иконка (круг внутри) */
.v-data-table .v-checkbox-btn .v-selection-control__input {
  color: #2e7d32 !important;
  background-color: transparent !important;
  width: 20px !important;
  height: 20px !important;
}

/* Выбранный чекбокс — зеленый фон */
.v-data-table .v-checkbox-btn.v-selection-control--dirty .v-selection-control__wrapper {
  background-color: #4caf50 !important;
  border-color: #2e7d32 !important;
}

/* Галочка в выбранном чекбоксе — белая */
.v-data-table .v-checkbox-btn.v-selection-control--dirty .v-selection-control__input .v-icon {
  color: white !important;
  opacity: 1 !important;
}

/* Hover эффект */
.v-data-table .v-checkbox-btn:hover .v-selection-control__wrapper {
  border-color: #1b5e20 !important;
  background-color: rgba(76, 175, 80, 0.1) !important;
}

/* Чекбокс в заголовке таблицы */
.v-data-table thead .v-checkbox-btn .v-selection-control__wrapper {
  border: 2px solid #2e7d32 !important;
}

/* Увеличиваем специфичность для гарантированного применения */
.v-application .v-data-table .v-checkbox-btn.v-selection-control--dirty {
  color: #4caf50 !important;
}
</style>