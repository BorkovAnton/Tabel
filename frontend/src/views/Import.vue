<template>
  <v-container>
    <h1 class="mb-4">Импорт данных</h1>

    <v-row>
      <!-- Импорт сотрудников -->
      <v-col cols="12" md="6">
        <v-card class="pa-4">
          <v-card-title>Загрузка сотрудников из Excel</v-card-title>
          <v-card-text>
            <v-file-input
              v-model="employeeFile"
              label="Выберите файл Excel"
              accept=".xlsx,.xls"
              prepend-icon="mdi-file-excel"
              show-size
              clearable
            ></v-file-input>

            <v-alert
              v-if="employeeError"
              type="error"
              closable
              class="mb-4"
              @click:close="employeeError = ''"
            >
              {{ employeeError }}
            </v-alert>

            <v-alert
              v-if="employeeResult"
              type="success"
              closable
              class="mb-4"
              @click:close="employeeResult = null"
            >
              Обработано: {{ employeeResult.stats.total }},
              создано: {{ employeeResult.stats.created }},
              уже существует: {{ employeeResult.stats.updated }},
              ошибок: {{ employeeResult.stats.errors }}
              <div v-if="employeeResult.errors.length">
                <div v-for="(err, i) in employeeResult.errors" :key="i">
                  Строка {{ err.row }}: {{ err.message }}
                </div>
              </div>
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="primary"
              :loading="employeeLoading"
              :disabled="!employeeFile"
              @click="uploadEmployees"
            >
              Загрузить сотрудников
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Импорт проходной -->
      <v-col cols="12" md="6">
        <v-card class="pa-4">
          <v-card-title>Загрузка проходной из Excel</v-card-title>
          <v-card-text>
            <v-file-input
              v-model="turnstileFile"
              label="Выберите файл Excel"
              accept=".xlsx,.xls"
              prepend-icon="mdi-file-excel"
              show-size
              clearable
            ></v-file-input>

            <v-alert
              v-if="turnstileError"
              type="error"
              closable
              class="mb-4"
              @click:close="turnstileError = ''"
            >
              {{ turnstileError }}
            </v-alert>

            <v-alert
              v-if="turnstileResult"
              type="success"
              closable
              class="mb-4"
              @click:close="turnstileResult = null"
            >
              Всего: {{ turnstileResult.stats.total }},
              распознано: {{ turnstileResult.stats.recognized }},
              не распознано: {{ turnstileResult.stats.unrecognized }},
              ошибок: {{ turnstileResult.stats.errors }}
              <div v-if="turnstileResult.errors.length">
                <div v-for="(err, i) in turnstileResult.errors" :key="i">
                  Строка {{ err.row }}: {{ err.message }}
                </div>
              </div>
            </v-alert>

            <!-- Список нераспознанных ФИО -->
            <div v-if="unrecognizedNames.length > 0" style="margin-top: 20px;">
              <h3 style="color: #d32f2f; margin-bottom: 10px;">
                ️ Нераспознанные ФИО ({{ unrecognizedNames.length }})
              </h3>
              <p style="color: #666; margin-bottom: 15px; font-size: 14px;">
                Эти ФИО из отчёта проходной не найдены в базе сотрудников. 
                Проверьте правильность написания в Excel-файле.
              </p>
              
              <v-table density="compact" hover>
                <thead>
                  <tr>
                    <th>ФИО из проходной</th>
                    <th style="text-align: right;">Количество записей</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in unrecognizedNames" :key="item.name">
                    <td>{{ item.name }}</td>
                    <td style="text-align: right;">{{ item.count }}</td>
                  </tr>
                </tbody>
              </v-table>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="primary"
              :loading="turnstileLoading"
              :disabled="!turnstileFile"
              @click="uploadTurnstile"
            >
              Загрузить проходную
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Расчёт табеля (служебный блок, виден только Администратору) -->
    <v-row v-if="auth.isAdmin">
      <v-col cols="12" md="6">
        <v-card class="pa-4">
          <v-card-title>Расчёт табеля</v-card-title>
          <v-card-text>
            <p style="color: #666; margin-bottom: 15px; font-size: 14px;">
              Выполняет расчёт фактического табеля за выбранный период по данным проходной и графиков.
            </p>

            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="calcDateFrom"
                  label="Дата с"
                  type="date"
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-calendar"
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="calcDateTo"
                  label="Дата по"
                  type="date"
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-calendar"
                ></v-text-field>
              </v-col>
            </v-row>

            <v-alert
              v-if="calcError"
              type="error"
              closable
              class="mb-4"
              @click:close="calcError = ''"
            >
              {{ calcError }}
            </v-alert>

            <v-alert
              v-if="calcResult"
              type="success"
              closable
              class="mb-4"
              @click:close="calcResult = null"
            >
              Расчёт завершён!<br>
              Обработано дней: {{ calcResult.total_days }},<br>
              Сотрудников: {{ calcResult.employees_processed }},<br>
              Создано записей: {{ calcResult.records_created }},<br>
              Обновлено записей: {{ calcResult.records_updated }},<br>
              Требуют проверки: {{ calcResult.needs_review_count }}
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="success"
              :loading="calcLoading"
              :disabled="!calcDateFrom || !calcDateTo"
              prepend-icon="mdi-calculator"
              @click="calculateTimesheet"
            >
              Рассчитать
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api'
import { auth } from '../auth'

const employeeFile = ref(null)
const employeeLoading = ref(false)
const employeeError = ref('')
const employeeResult = ref(null)

const turnstileFile = ref(null)
const turnstileLoading = ref(false)
const turnstileError = ref('')
const turnstileResult = ref(null)
const unrecognizedNames = ref([])

// Расчёт табеля
const calcDateFrom = ref('')
const calcDateTo = ref('')
const calcLoading = ref(false)
const calcError = ref('')
const calcResult = ref(null)

// По умолчанию — текущий месяц
;(function initCalcPeriod() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const lastDay = new Date(y, now.getMonth() + 1, 0).getDate()
  calcDateFrom.value = `${y}-${m}-01`
  calcDateTo.value = `${y}-${m}-${String(lastDay).padStart(2, '0')}`
})()

async function calculateTimesheet() {
  if (!calcDateFrom.value || !calcDateTo.value) return

  calcLoading.value = true
  calcError.value = ''
  calcResult.value = null

  try {
    const response = await api.post('/api/timesheet/calculate', {
      employee_id: null,
      date_from: calcDateFrom.value,
      date_to: calcDateTo.value
    })
    calcResult.value = response.data
  } catch (e) {
    calcError.value = e.response?.data?.detail || 'Ошибка при расчёте табеля'
    console.error(e)
  } finally {
    calcLoading.value = false
  }
}

function extractFile(fileValue) {
  return Array.isArray(fileValue) ? fileValue[0] : fileValue
}

async function uploadEmployees() {
  const file = extractFile(employeeFile.value)
  if (!file) return

  employeeLoading.value = true
  employeeError.value = ''
  employeeResult.value = null

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await api.post('/employees/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    employeeResult.value = response.data
  } catch (e) {
    employeeError.value = e.response?.data?.detail || 'Ошибка загрузки файла сотрудников'
  } finally {
    employeeLoading.value = false
  }
}

async function uploadTurnstile() {
  const file = extractFile(turnstileFile.value)
  if (!file) return

  turnstileLoading.value = true
  turnstileError.value = ''
  turnstileResult.value = null
  unrecognizedNames.value = []

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await api.post('/api/turnstile/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    turnstileResult.value = response.data
    
    // Загружаем список нераспознанных ФИО
    await loadUnrecognizedNames()
  } catch (e) {
    turnstileError.value = e.response?.data?.detail || 'Ошибка загрузки файла проходной'
  } finally {
    turnstileLoading.value = false
  }
}

async function loadUnrecognizedNames() {
  try {
    const response = await api.get('/api/turnstile/unrecognized')
    const events = response.data
    
    // Группируем по raw_name и считаем количество
    const nameCount = {}
    events.forEach(event => {
      const name = event.raw_name
      nameCount[name] = (nameCount[name] || 0) + 1
    })
    
    // Преобразуем в массив и сортируем по количеству (больше сначала)
    unrecognizedNames.value = Object.entries(nameCount)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
  } catch (error) {
    console.error('Ошибка загрузки нераспознанных:', error)
  }
}
</script>