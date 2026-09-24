<template>
  <v-container>
    <h1 class="mb-4">События проходной</h1>

    <v-btn color="primary" class="mb-4" @click="showAddDialog = true">
      <v-icon left>mdi-plus</v-icon>
      Добавить событие
    </v-btn>

    <v-alert v-if="error" type="error" closable @click:close="error = ''">
      {{ error }}
    </v-alert>

    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-text-field
          v-model.number="filterEmployeeId"
          label="ID сотрудника"
          type="number"
          clearable
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="filterDate"
          label="Дата (YYYY-MM-DD)"
          placeholder="2026-09-08"
          clearable
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="4">
        <v-btn color="secondary" @click="loadEvents">
          Фильтровать
        </v-btn>
      </v-col>
    </v-row>

    <v-data-table
      :headers="headers"
      :items="events"
      :loading="loading"
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
      <template v-slot:item.is_recognized="{ item }">
        <v-icon :color="item.is_recognized ? 'green' : 'red'">
          {{ item.is_recognized ? 'mdi-check' : 'mdi-close' }}
        </v-icon>
      </template>
    </v-data-table>

    <!-- Диалог добавления события -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>Добавить событие проходной</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newEvent.raw_name"
            label="ФИО *"
            required
          ></v-text-field>
          <v-text-field
            v-model="newEvent.datetime"
            label="Дата и время *"
            placeholder="08.09.2026 08:00"
            required
          ></v-text-field>
          <v-select
            v-model="newEvent.event_type"
            :items="['in', 'out']"
            label="Тип события *"
            required
          ></v-select>
          <v-text-field
            v-model.number="newEvent.employee_id"
            label="ID сотрудника (опционально)"
            type="number"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showAddDialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="addEvent" :loading="adding">
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

const events = ref([])
const loading = ref(false)
const error = ref('')
const showAddDialog = ref(false)
const adding = ref(false)
const filterEmployeeId = ref(null)
const filterDate = ref('')

const newEvent = ref({
  raw_name: '',
  datetime: '',
  event_type: 'in',
  employee_id: null
})

const headers = [
  { title: 'ID', key: 'id' },
  { title: 'ФИО', key: 'raw_name' },
  { title: 'Сотрудник ID', key: 'employee_id' },
  { title: 'Дата и время', key: 'datetime' },
  { title: 'Тип', key: 'event_type' },
  { title: 'Распознано', key: 'is_recognized' }
]

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('ru-RU')
}

async function loadEvents() {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filterEmployeeId.value) params.employee_id = filterEmployeeId.value
    if (filterDate.value) params.date = filterDate.value
    
    const response = await api.get('/api/turnstile', { params })
    events.value = response.data
  } catch (e) {
    error.value = 'Ошибка загрузки событий'
  } finally {
    loading.value = false
  }
}

async function addEvent() {
  if (!newEvent.value.raw_name || !newEvent.value.datetime || !newEvent.value.event_type) {
    error.value = 'Заполните обязательные поля'
    return
  }

  adding.value = true
  error.value = ''
  try {
    await api.post('/api/turnstile/', newEvent.value)
    showAddDialog.value = false
    newEvent.value = {
      raw_name: '',
      datetime: '',
      event_type: 'in',
      employee_id: null
    }
    await loadEvents()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка добавления события'
  } finally {
    adding.value = false
  }
}

onMounted(() => {
  loadEvents()
})
</script>