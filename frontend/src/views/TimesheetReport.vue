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
            <v-autocomplete
              v-model="selectedDepartment"
              :items="sortedDepartments"
              item-title="title"
              item-value="id"
              label="Подразделение"
              variant="outlined"
              density="comfortable"
              clearable
              prepend-inner-icon="mdi-office-building"
              placeholder="Начните вводить название…"
              no-data-text="Подразделение не найдено"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props" :title="item.raw.name">
                  <template #prepend>
                    <v-icon icon="mdi-office-building" size="small" class="mr-2" />
                  </template>
                  <template #append>
                    <v-chip
                      v-if="item.raw.employee_count != null"
                      size="x-small"
                      variant="tonal"
                      color="grey"
                    >
                      {{ item.raw.employee_count }} сотр.
                    </v-chip>
                  </template>
                </v-list-item>
              </template>
            </v-autocomplete>
          </v-col>
          <v-col cols="12" md="3" class="d-flex align-end">
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
          <v-col v-if="auth.isAdmin" cols="12" md="3" class="d-flex align-end">
            <v-btn
              color="success"
              variant="outlined"
              size="large"
              class="flex-grow-1"
              :loading="recalcLoading"
              prepend-icon="mdi-file-document-check-outline"
              @click="recalculateWithDocuments"
            >
              Пересчитать по документам
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

    <!-- Легенда подсветки ячеек -->
    <v-card v-if="reportData" class="mb-4 pa-4" elevation="2">
      <div class="text-subtitle-1 font-weight-bold mb-2">Легенда подсветки</div>
      <div class="text-caption text-grey mb-2">
        Порог переработки из настроек расчёта:
        <b v-if="overtimeThresholdMin > 0">{{ overtimeThresholdMin }} мин</b>
        <b v-else>0 (считается любая переработка)</b>.
        Переработка в пределах порога не считается сверхурочной — ячейка остаётся зелёной.
      </div>
      <div class="d-flex flex-wrap legend-row">
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch work-in-document-cell"></span>
          <span>Работа в период документа (часы факт)</span>
        </div>
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch norm-met-cell"></span>
          <span>Норма выполнена / переработка ≤ порога</span>
        </div>
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch overtime-cell"></span>
          <span>Сверхурочные</span>
        </div>
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch underwork-cell"></span>
          <span>Недовыработка</span>
        </div>
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch review-cell"></span>
          <span>Требует проверки</span>
        </div>
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch cell-from-document"></span>
          <span>По документу, без фактических часов</span>
        </div>
        <div class="d-flex align-center legend-item">
          <span class="legend-swatch weekend-cell"></span>
          <span>Выходной</span>
        </div>
      </div>
    </v-card>

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
                >
                  <v-tooltip location="bottom" :max-width="200">
                    <template #activator="{ props: tooltipProps }">
                      <span v-bind="tooltipProps" class="cell-content" v-html="formatCellValue(emp.days[day])"></span>
                    </template>
                    <div class="day-tooltip">
                      <div class="font-weight-bold mb-1">{{ tooltipDateLabel(day) }}</div>
                      <!-- Работа в период документа: документ есть, но сотрудник приходил -->
                      <div v-if="isWorkInDocument(emp.days[day])" class="mb-1">
                        <v-chip color="purple" size="x-small">📄 Работа в период: {{ emp.days[day].document_code }}</v-chip>
                        <div v-if="emp.days[day]?.review_reason" class="text-caption mt-1">{{ emp.days[day].review_reason }}</div>
                      </div>
                      <div v-else-if="emp.days[day]?.document_code" class="mb-1">
                        <v-chip color="info" size="x-small">Документ: {{ emp.days[day].document_code }}</v-chip>
                        <div v-if="emp.days[day]?.review_reason" class="text-caption mt-1">{{ emp.days[day].review_reason }}</div>
                      </div>
                      <div v-else-if="emp.days[day]?.needs_review" class="mb-1">
                        <v-chip color="red" size="x-small">⚠ Требует проверки</v-chip>
                        <div v-if="emp.days[day]?.review_reason" class="text-caption mt-1">{{ emp.days[day].review_reason }}</div>
                      </div>
                      <div class="d-flex align-center ga-1">
                        <v-icon size="x-small" icon="mdi-login" color="green-darken-2"></v-icon>
                        Вход: {{ emp.days[day]?.first_in || '—' }}
                      </div>
                      <div class="d-flex align-center ga-1">
                        <v-icon size="x-small" icon="mdi-logout" color="red-darken-2"></v-icon>
                        Выход: {{ emp.days[day]?.last_out || '—' }}
                      </div>
                      <div v-if="emp.days[day]?.overtime" class="d-flex align-center ga-1 text-orange-darken-2">
                        <v-icon size="x-small" icon="mdi-clock-alert-outline"></v-icon>
                        Сверхурочно: {{ formatTime(emp.days[day].overtime) }}
                      </div>
                      <!-- Индикатор «норма выполнена»: факт = норма либо переработка ≤ порога из настроек -->
                      <div v-else-if="isNormMet(emp.days[day])" class="d-flex align-center ga-1 norm-indicator">
                        <v-icon size="x-small" icon="mdi-check-circle"></v-icon>
                        <template v-if="Number(emp.days[day]?.hours || 0) > Number(emp.days[day]?.default_hours || 0) + NORM_TOLERANCE && hasNorm(emp.days[day])">
                          Переработка {{ formatTime(Math.max(0, Number(emp.days[day].hours) - Number(emp.days[day].default_hours))) }} ≤ порога ({{ overtimeThresholdMin }} мин) — не сверхурочная
                        </template>
                        <template v-else>✅ Норма выполнена</template>
                      </div>
                      <!-- Индикатор недовыработки: факт < нормы (за пределами допуска) -->
                      <div v-else-if="isUnderwork(emp.days[day])" class="d-flex align-center ga-1 underwork-indicator">
                        <v-icon size="x-small" icon="mdi-arrow-down-bold-outline"></v-icon>
                        Недовыработка: {{ formatTime(Math.max(0, Number(emp.days[day].default_hours) - Number(emp.days[day].hours || 0)) ) }}
                      </div>
                      <v-divider class="my-1"></v-divider>
                      <div class="d-flex align-center ga-1 font-weight-medium">
                        <v-icon size="x-small" icon="mdi-calendar-clock" color="blue-darken-2"></v-icon>
                        {{ emp.days[day]?.hours ? ('Всего: ' + formatTime(emp.days[day].hours)) : 'Данные отсутствуют' }}
                      </div>
                      <div v-if="hasNorm(emp.days[day])" class="d-flex align-center ga-1">
                        <v-icon size="x-small" icon="mdi-target" color="blue-darken-2"></v-icon>
                        Норма по графику: {{ formatTime(Number(emp.days[day].default_hours)) }} ч
                      </div>
                    </div>
                  </v-tooltip>
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
      Выберите месяц и год, затем нажмите "Сформировать". Расчёт табеля выполняется на вкладке «Импорт».
    </v-alert>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'
import { auth } from '../auth'

// Допуск при сравнении факта с нормой: 5 минут в часах (0.083 ч).
// Нужен, потому что при округлении могут быть расхождения в несколько секунд.
const NORM_TOLERANCE = 0.083

// Порог переработки из «Настроек расчёта» (минуты). Применяется ко всем графикам:
// если переработка не превышает порог — она НЕ считается сверхурочной,
// и ячейка остаётся зелёной («норма выполнена»). Например, при пороге 30 мин:
// переработка 15 мин → сверхурочные = 0 (зелёная), переработка 36 мин → жёлтая.
const overtimeThresholdMin = ref(0)

async function loadOvertimeThreshold() {
  try {
    const { data } = await api.get('/company-settings/')
    overtimeThresholdMin.value = Number(data.overtime_threshold ?? 0) || 0
  } catch (e) {
    // Если настройки недоступны — считаем порог равным 0 (старое поведение)
    console.error('Ошибка загрузки настроек расчёта:', e)
    overtimeThresholdMin.value = 0
  }
}

onMounted(loadOvertimeThreshold)

const loading = ref(false)
const excelLoading = ref(false)
const recalcLoading = ref(false)
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

// Подразделения: сортировка по алфавиту (регистронезависимо).
// В title кладём также имя — v-autocomplete фильтрует по подстроке регистронезависимо,
// поэтому «швейн» найдёт «Участок швейных».
const sortedDepartments = computed(() => {
  return [...departments.value]
    .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
    .map(d => ({ ...d, title: d.name }))
})

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
    const response = await api.get("/departments/?flat=true")
    departments.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки подразделений:', e)
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

async function recalculateWithDocuments() {
  // Явный пересчёт фактического табеля за выбранный месяц
  // с учётом активных документов («Документы и приказы»)
  recalcLoading.value = true
  error.value = ''
  try {
    const lastDay = new Date(selectedYear.value, selectedMonth.value, 0).getDate()
    const pad = (n) => String(n).padStart(2, '0')
    const resp = await api.post('/api/timesheet/calculate', {
      date_from: `${selectedYear.value}-${pad(selectedMonth.value)}-01`,
      date_to: `${selectedYear.value}-${pad(selectedMonth.value)}-${pad(lastDay)}`,
    })
    const d = resp.data || {}
    alert(`Пересчёт завершён: создано ${d.records_created ?? 0}, обновлено ${d.records_updated ?? 0} записей, по документам заполнено дней: ${d.documents_applied ?? 0}`)
    await generateReport()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка пересчёта табеля'
  } finally {
    recalcLoading.value = false
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

  // ФИОЛЕТОВЫЙ: работа в период документа (сотрудника вызвали на работу
  // в отпуск/командировку — есть документ И фактические часы > 0)
  const factForDoc = Number(dayData.hours) || 0
  if (dayData.document_code && factForDoc > 0) return 'work-in-document-cell'
  if (dayData.document_code) return 'cell-from-document'
  if (val === 'О6' || dayData.needs_review) return 'review-cell'
  if (val === 'в') return 'weekend-cell'

  // Числовые ячейки: сравниваем факт (hours) с нормой по графику (default_hours)
  const fact = Number(dayData.hours) || 0
  const hasNorm = dayData.default_hours !== null && dayData.default_hours !== undefined
  const norm = hasNorm ? Number(dayData.default_hours) : 0

  if (fact > 0 && hasNorm && norm > 0) {
    // ЖЁЛТЫЙ: переработка СВЕРХ порога из «Настроек расчёта» (минуты).
    // Если переработка не превышает порог — она не считается сверхурочной,
    // и ячейка остаётся зелёной («норма выполнена»).
    if (isRealOvertime(dayData)) return 'overtime-cell'
    // ✅ ЗЕЛЁНЫЙ: норма выполнена (переработка в пределах порога/допуска)
    if (isNormMet(dayData)) return 'norm-met-cell'
    // РОЗОВЫЙ: недовыработка (факт меньше нормы с учётом допуска)
    if (isUnderwork(dayData)) return 'underwork-cell'
  }

  // Фолбэк для старых данных без default_hours: формат "10.25 (2.25с)"
  if (val.includes('с')) return 'overtime-cell'
  return 'work-cell'
}

// 📄 Работа в период документа: на день есть активный документ (отпуск,
// командировка и т.п.), но сотрудник фактически приходил (часы > 0).
function isWorkInDocument(dayData) {
  if (!dayData || !dayData.document_code) return false
  return (Number(dayData.hours) || 0) > 0
}

// Есть ли у ячейки норма по графику (default_hours > 0)
function hasNorm(dayData) {
  if (!dayData) return false
  return dayData.default_hours !== null && dayData.default_hours !== undefined
    && Number(dayData.default_hours) > 0
}

// Сверхурочные с учётом порога из «Настроек расчёта» (минуты):
// если переработка (факт − норма) в минутах НЕ превышает порог — она не считается
// сверхурочной. Порог 0 = любое превышение (вне допуска ±5 мин) — сверхурочные.
// Логика полностью повторяет backend apply_overtime_threshold().
function isRealOvertime(dayData) {
  if (!dayData || !hasNorm(dayData)) return false
  const fact = Number(dayData.hours) || 0
  if (fact <= 0) return false
  // Если бэкенд уже посчитал сверхурочные (> 0) — они точно есть
  if (Number(dayData.overtime) > 0) return true
  const overMin = Math.round((fact - Number(dayData.default_hours)) * 60 * 1000000) / 1000000
  if (overMin <= NORM_TOLERANCE * 60) return false // в пределах допуска округления
  return overMin > overtimeThresholdMin.value
}

// ✅ Норма выполнена: факт равен норме (допуск ±5 мин) ЛИБО переработка не
// превышает порог из настроек расчёта (сверхурочные = 0) — день отработан корректно.
// Порог влияет только на переработки: недовыработка остаётся розовой при любом пороге.
function isNormMet(dayData) {
  if (!dayData || !hasNorm(dayData)) return false
  const fact = Number(dayData.hours) || 0
  if (fact <= 0) return false
  if (isRealOvertime(dayData)) return false
  const diffHours = fact - Number(dayData.default_hours)
  if (diffHours > 0) {
    // Переработка в пределах порога → «норма выполнена» (зелёный)
    return diffHours <= Math.max(NORM_TOLERANCE, overtimeThresholdMin.value / 60)
  }
  // Факт <= нормы: зелёный только если разница в допуске округления (±5 мин)
  return Math.abs(diffHours) <= NORM_TOLERANCE
}

// ↓ Недовыработка: факт меньше нормы за пределами допуска
function isUnderwork(dayData) {
  if (!dayData || !hasNorm(dayData)) return false
  const fact = Number(dayData.hours) || 0
  if (fact <= 0) return false
  return fact < Number(dayData.default_hours) - NORM_TOLERANCE
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

// Название месяца для tooltip (полное, с родительным падежом)
const MONTH_NAMES_GENITIVE = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

// Метка даты в tooltip: «Понедельник, 28 сентября 2026»
function tooltipDateLabel(day) {
  if (!reportData.value) return ''
  const y = reportData.value.year
  const m = reportData.value.month
  const date = new Date(y, m - 1, day)
  const weekdays = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
  return `${weekdays[date.getDay()]}, ${day} ${MONTH_NAMES_GENITIVE[m - 1]} ${y}`
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

/* Содержимое ячейки дня (activator для tooltip) — растягиваем на всю ячейку,
   чтобы tooltip открывался при наведении в любом месте ячейки */
.cell-content {
  display: block;
  width: 100%;
  height: 100%;
  cursor: default;
}

.cell-from-document {
  background-color: #e8f5e9 !important;
  border: 1px dashed #4caf50;
}

/* 📄 ФИОЛЕТОВЫЙ: работа в период документа (отпуск/командировка, но сотрудник приходил) */
.work-in-document-cell {
  background-color: #f3e5f5 !important;
  border: 2px solid #9c27b0 !important;
  color: #4a148c !important;
  font-weight: bold;
}

.work-in-document-cell:hover {
  background-color: #e1bee7 !important;
}

/* Содержимое tooltip с деталями дня */
.day-tooltip {
  font-size: 0.8rem;
  line-height: 1.5;
  white-space: nowrap;
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

/* ✅ ЗЕЛЁНЫЙ: норма выполнена (факт = норма, допуск ±5 минут) */
.norm-met-cell {
  background-color: #e8f5e9 !important;  /* светло-зелёный фон */
  border: 1px solid #4caf50 !important;  /* зелёная рамка */
  color: #1b5e20 !important;             /* тёмно-зелёный текст */
}

.norm-met-cell:hover {
  background-color: #c8e6c9 !important;  /* более тёмный зелёный при наведении */
}

/* Индикатор «Норма выполнена» в tooltip */
.norm-indicator {
  color: #c8e6c9;
}

/* РОЗОВЫЙ: недовыработка (факт меньше нормы) */
.underwork-cell {
  background-color: #fce4ec !important;  /* светло-розовый фон */
  border: 1px solid #f48fb1 !important;  /* розовая рамка */
  color: #880e4f !important;             /* тёмно-розовый текст */
}

.underwork-cell:hover {
  background-color: #f8bbd0 !important;
}

/* Индикатор недовыработки в tooltip */
.underwork-indicator {
  color: #f8bbd0;
}

/* Легенда подсветки ячеек */
.legend-row {
  gap: 16px;
}

.legend-item {
  font-size: 0.85rem;
}

.legend-swatch {
  display: inline-block;
  width: 24px;
  height: 24px;
  margin-right: 8px;
  border-radius: 3px;
  flex-shrink: 0;
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