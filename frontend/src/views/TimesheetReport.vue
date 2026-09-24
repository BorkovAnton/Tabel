<template>
  <v-container fluid class="pa-6">
    <!-- Заголовок -->
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4 font-weight-bold">Табель фактический</h1>
      <v-btn color="success" size="large" @click="downloadExcel" :loading="excelLoading">
        <v-icon start>mdi-file-excel</v-icon>
        Скачать Excel
      </v-btn>
    </div>
    
    <!-- Фильтры -->
    <v-card class="mb-6" elevation="2">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedMonth"
              :items="months"
              item-title="title"
              item-value="value"
              label="Месяц"
              variant="outlined"
              density="comfortable"
              prepend-inner-icon="mdi-calendar-month"
            ></v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedYear"
              :items="years"
              label="Год"
              variant="outlined"
              density="comfortable"
              prepend-inner-icon="mdi-calendar"
            ></v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedDepartment"
              :items="departments"
              item-title="name"
              item-value="id"
              label="Подразделение"
              variant="outlined"
              density="comfortable"
              clearable
              prepend-inner-icon="mdi-office-building"
            ></v-select>
          </v-col>
          <v-col cols="12" md="3" class="d-flex align-end">
            <v-btn 
              color="success" 
              size="large"
              class="flex-grow-1 mr-2"
              @click="calculateTimesheet"
              :loading="calculating"
              prepend-icon="mdi-calculator"
            >
              Рассчитать
            </v-btn>
            <v-btn 
              color="primary" 
              size="large"
              class="flex-grow-1"
              @click="generateReport"
              :loading="loading"
              prepend-icon="mdi-refresh"
            >
              Сформировать
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Статистика -->
    <v-row v-if="reportData" class="mb-6">
      <v-col cols="12" md="3">
        <v-card elevation="2" color="blue">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Всего сотрудников</div>
            <div class="text-h3 font-weight-bold">{{ reportData.employees.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="green">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Отработано часов</div>
            <div class="text-h3 font-weight-bold">{{ totalHours }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="orange">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Сверхурочных</div>
            <div class="text-h3 font-weight-bold">{{ overtimeHours }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2" color="red">
          <v-card-text class="text-white">
            <div class="text-subtitle-2 opacity-75">Требует проверки</div>
            <div class="text-h3 font-weight-bold">{{ needsReviewCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Сообщение об ошибке -->
    <v-alert v-if="error" type="error" variant="tonal" closable class="mb-4">
      {{ error }}
    </v-alert>

    <!-- Таблица табеля -->
    <v-card v-if="reportData" elevation="2">
      <v-card-text class="pa-0">
        <div style="overflow-x: auto; max-height: 70vh;">
          <table class="timesheet-table">
            <colgroup>
              <col style="width: 40px;">
              <col style="width: 180px;">
              <col style="width: 220px;">
              <col v-for="day in reportData.days_in_month" :key="day" style="width: 45px;">
              <col style="width: 80px;">
            </colgroup>
            <thead>
              <tr class="bg-grey-lighten-4">
                <th class="sticky-col font-weight-bold">№</th>
                <th class="sticky-col-2 font-weight-bold">Ф.И.О.</th>
                <th class="sticky-col-3 font-weight-bold">Подразделение</th>
                <th 
                  v-for="day in reportData.days_in_month" 
                  :key="day" 
                  class="text-center font-weight-bold"
                  :class="isWeekend(day) ? 'bg-blue-lighten-5' : ''"
                >
                  <div>{{ getDayOfWeek(day, reportData.year, reportData.month) }}</div>
                  <div class="text-caption">{{ day }}</div>
                </th>
                <th class="sticky-col-end text-center font-weight-bold bg-grey-lighten-3">
                  Итого часов
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="emp in reportData.employees" :key="emp.index">
                <td class="sticky-col text-center">{{ emp.index }}</td>
                <td class="sticky-col-2 font-weight-medium">{{ emp.full_name }}</td>
                <td class="sticky-col-3 text-grey">{{ emp.department }}</td>
                
                <td 
                  v-for="day in reportData.days_in_month" 
                  :key="day" 
                  class="text-center timesheet-cell"
                  :class="getCellClasses(emp.days[day], day)"
                  v-html="formatCellValue(emp.days[day])"
                >
                </td>
                
                <td class="sticky-col-end text-center font-weight-bold bg-grey-lighten-4">
                  {{ emp.total_hours }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </v-card-text>
    </v-card>

    <v-alert v-else-if="!loading" type="info" variant="tonal" class="mt-4">
      Выберите месяц и год, затем нажмите "Рассчитать" или "Сформировать"
    </v-alert>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const loading = ref(false)
const calculating = ref(false)
const excelLoading = ref(false)
const error = ref('')
const reportData = ref(null)

const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())
const selectedDepartment = ref(null)

const departments = ref([])
const months = ref([
  { title: 'Январь', value: 1 }, { title: 'Февраль', value: 2 },
  { title: 'Март', value: 3 }, { title: 'Апрель', value: 4 },
  { title: 'Май', value: 5 }, { title: 'Июнь', value: 6 },
  { title: 'Июль', value: 7 }, { title: 'Август', value: 8 },
  { title: 'Сентябрь', value: 9 }, { title: 'Октябрь', value: 10 },
  { title: 'Ноябрь', value: 11 }, { title: 'Декабрь', value: 12 }
])
const currentYear = new Date().getFullYear()
const years = ref(Array.from({ length: 7 }, (_, i) => currentYear - 3 + i))

// Вычисляемые значения
const totalHours = computed(() => {
  if (!reportData.value) return 0
  return reportData.value.employees.reduce((sum, emp) => sum + emp.total_hours, 0).toFixed(1)
})

const overtimeHours = computed(() => {
  if (!reportData.value) return 0
  return '0'
})

const needsReviewCount = computed(() => {
  if (!reportData.value) return 0
  let count = 0
  reportData.value.employees.forEach(emp => {
    Object.values(emp.days).forEach(day => {
      if (day && day.needs_review) count++
    })
  })
  return count
})

async function loadDepartments() {
  try {
    const response = await api.get('/departments/?flat=true')
    departments.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки подразделений:', e)
  }
}

async function calculateTimesheet() {
  calculating.value = true
  error.value = ''
  
  try {
    const year = selectedYear.value
    const month = selectedMonth.value
    
    const dateFrom = `${year}-${String(month).padStart(2, '0')}-01`
    const lastDay = new Date(year, month, 0).getDate()
    const dateTo = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
    
    const response = await api.post('/api/timesheet/calculate', {
      employee_id: null,
      date_from: dateFrom,
      date_to: dateTo
    })
    
    const data = response.data
    alert(
      `Расчёт завершён!\n\n` +
      `Обработано дней: ${data.total_days}\n` +
      `Сотрудников: ${data.employees_processed}\n` +
      `Создано записей: ${data.records_created}\n` +
      `Обновлено записей: ${data.records_updated}\n` +
      `Требуют проверки: ${data.needs_review_count}`
    )
    
    // Автоматически формируем отчёт после расчёта
    await generateReport()
    
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка при расчёте табеля'
    console.error(e)
  } finally {
    calculating.value = false
  }
}

async function generateReport() {
  loading.value = true
  error.value = ''
  reportData.value = null
  
  try {
    const params = {
      month: selectedMonth.value,
      year: selectedYear.value
    }
    if (selectedDepartment.value) {
      params.department_id = selectedDepartment.value
    }
    
    const response = await api.get('/api/timesheet/report', { params })
    reportData.value = response.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка формирования отчета'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function downloadExcel() {
  excelLoading.value = true
  error.value = ''
  
  try {
    const params = {
      month: selectedMonth.value,
      year: selectedYear.value
    }
    if (selectedDepartment.value) {
      params.department_id = selectedDepartment.value
    }
    
    const response = await api.get('/api/timesheet/report/excel', { 
      params,
      responseType: 'blob' 
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    
    const monthName = months.value.find(m => m.value === selectedMonth.value)?.title || 'месяц'
    link.setAttribute('download', `Табель_${monthName}_${selectedYear.value}.xlsx`)
    
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    error.value = 'Ошибка скачивания Excel файла'
    console.error(e)
  } finally {
    excelLoading.value = false
  }
}

function getCellClasses(dayData, day) {
  if (!dayData) return isWeekend(day) ? 'weekend-cell' : ''
  const val = dayData.value
  
  if (val === 'О6' || dayData.needs_review) return 'review-cell'
  if (val.includes('с')) return 'overtime-cell'  // Сверхурочные (формат "10.25 (2.25с)")
  if (val === 'в') return 'weekend-cell'
  return 'work-cell'
}

function formatCellValue(dayData) {
  if (!dayData) return 'в'
  const val = dayData.value
  
  // Если есть сверхурочные (формат "10.25 (2.25с)")
  if (val.includes('с')) {
    const match = val.match(/([\d.]+)\s+\(([\d.]+)с\)/)
    if (match) {
      const hours = parseFloat(match[1])
      const overtime = parseFloat(match[2])
      return `${formatTime(hours)}<br><span style="font-size:0.65rem; color:#f57f17">(${formatTime(overtime)}с)</span>`
    }
    return val
  }
  
  // Если это число (обычные часы)
  if (!isNaN(val) && val !== 'О6') {
    return formatTime(parseFloat(val))
  }
  
  return val
}

function formatTime(decimalHours) {
  // Конвертируем десятичные часы в формат ЧЧ:ММ
  const hours = Math.floor(decimalHours)
  const minutes = Math.round((decimalHours - hours) * 60)
  return `${hours}:${String(minutes).padStart(2, '0')}`
}

function isWeekend(day) {
  if (!reportData.value) return false
  const date = new Date(reportData.value.year, reportData.value.month - 1, day)
  const dayOfWeek = date.getDay()
  return dayOfWeek === 0 || dayOfWeek === 6
}

function getDayOfWeek(day, year, month) {
  const date = new Date(year, month - 1, day)
  const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
  return days[date.getDay()]
}

onMounted(() => {
  loadDepartments()
})
</script>

<style scoped>
/* Таблица */
.timesheet-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.75rem;
  table-layout: fixed;
  box-sizing: border-box;
}

.timesheet-table th,
.timesheet-table td {
  border: 1px solid #e0e0e0;
  padding: 4px 2px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-sizing: border-box;
}

/* Липкие колонки */
.sticky-col { 
  position: sticky; 
  left: 0; 
  background: white !important; 
  z-index: 10; 
}

.sticky-col-2 { 
  position: sticky; 
  left: 40px; 
  background: white !important; 
  z-index: 10; 
  text-align: left;
  padding-left: 6px;
}

.sticky-col-3 { 
  position: sticky; 
  left: 220px; 
  background: white !important; 
  z-index: 10; 
  text-align: left;
  padding-left: 6px;
}

.sticky-col-end { 
  position: sticky; 
  right: 0; 
  background: #f5f5f5 !important; 
  z-index: 10;
}

/* Заголовки дней */
.timesheet-table thead th:not([class^="sticky-"]) {
  padding: 6px 2px;
  font-size: 0.7rem;
  height: 50px;
  vertical-align: middle;
}

/* Ячейки с днями */
.timesheet-table tbody td:not([class^="sticky-"]) {
  padding: 6px 2px;
  font-size: 0.75rem;
  line-height: 1.3;
  vertical-align: top;
  height: 48px;
}

/* Заголовок последней колонки */
.sticky-col-end th {
  font-size: 0.7rem;
  white-space: nowrap !important;
}

/* Ячейка последней колонки */
.sticky-col-end td {
  font-weight: bold !important;
  white-space: nowrap !important;
}

/* Цвета ячеек */
.weekend-cell { 
  background-color: #e3f2fd !important; 
  color: #1976d2;
}

.work-cell { 
  background-color: white !important; 
}

.overtime-cell { 
  background-color: #fff9c4 !important; 
  color: #f57f17;
  font-weight: bold;
  font-size: 0.7rem;
  line-height: 1.2;
  white-space: normal !important;
  word-break: break-word;
}

.review-cell { 
  background-color: #ffcdd2 !important; 
  color: #c62828;
  font-weight: bold;
}

/* Hover эффекты */
.timesheet-table tbody tr:hover td {
  background-color: #f5f5f5 !important;
}

.timesheet-table tbody tr:hover .sticky-col,
.timesheet-table tbody tr:hover .sticky-col-2,
.timesheet-table tbody tr:hover .sticky-col-3 {
  background-color: #f5f5f5 !important;
}

.timesheet-table tbody tr:hover .sticky-col-end {
  background-color: #eeeeee !important;
}

/* Адаптивность */
@media (max-width: 768px) {
  .timesheet-table {
    font-size: 0.65rem;
  }
  
  .timesheet-table th,
  .timesheet-table td {
    padding: 3px 1px;
  }
}
</style>