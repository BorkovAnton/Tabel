<template>
  <div class="t13-page" v-if="tabel">
    <!-- Шапка УТВЕРЖДАЮ -->
    <div class="t13-approve">
      <div class="approve-right">
        <div class="approve-label">УТВЕРЖДАЮ</div>
        <div class="approve-position">{{ directorPosition }}</div>
        <div class="approve-company">{{ companyName }}</div>
        <div class="approve-sign">_________________ {{ directorName }}</div>
        <div class="approve-date">"___" ____________ 20__г.</div>
      </div>
    </div>

    <!-- Заголовок -->
    <div class="t13-header">
      <h1 class="t13-title">Табель учёта рабочего времени за {{ monthName }} {{ tabel.year }} года</h1>
      <h2 class="t13-subtitle">Наименование структурного подразделения: {{ tabel.department_name || '—' }}</h2>
    </div>

    <!-- Таблица -->
    <table class="t13-table">
      <thead>
        <!-- Первый уровень заголовков -->
        <tr>
          <th rowspan="2" class="col-num">№</th>
          <th rowspan="2" class="col-fio">ФИО</th>
          <th rowspan="2" class="col-tabno">Таб. №</th>
          <th :colspan="tabel.days_in_month" class="col-days-header">Числа месяца</th>
          <th v-for="col in summaryColumns" :key="col.key" rowspan="2"
              class="col-summary-header" :class="{ 'col-overtime': col.key === 'overtime_hours' }">
            <!-- Заголовок колонки сверхурочных в две строки -->
            <template v-if="col.key === 'overtime_hours'">
              <span class="ot-main">Сверхурочные часы итого</span>
              <span class="ot-sub">(Сверхурочные часы без дней)</span>
            </template>
            <template v-else>{{ col.label }}</template>
          </th>
        </tr>
        <tr>
          <!-- Дни месяца -->
          <th v-for="d in tabel.days_in_month" :key="d" class="col-day-header"
              :class="{ 'cell-weekend': isWeekend(d), 'cell-holiday': isHoliday(d) }">
            <div class="day-name">{{ getDayOfWeekShort(d) }}</div>
            <div class="day-number">{{ d }}</div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in tabel.entries" :key="row.employee_id">
          <td class="col-num">{{ idx + 1 }}</td>
          <td class="col-fio">{{ row.full_name }}</td>
          <td class="col-tabno">{{ row.tab_number || '—' }}</td>

          <!-- Дни месяца: ДВЕ строки (код сверху, часы снизу) -->
          <td v-for="d in tabel.days_in_month" :key="d" class="col-day-cell"
              :class="{ 'cell-weekend': isWeekend(d), 'cell-holiday': isHoliday(d) }">
            <div class="day-code">{{ getCellCode(row.days[d]) }}</div>
            <div class="day-hours">{{ getCellHours(row.days[d], row, d, timeCodes) }}</div>
          </td>

          <!-- Итоговые колонки — ТОЧНО КАК В ТАБЕЛЕ ЗАПОЛНЕНИЯ (общий модуль tabelCalculations) -->
          <td v-for="col in summaryColumns" :key="col.key" class="col-summary-cell"
              :class="{ 'col-overtime-cell': col.key === 'overtime_hours' }">
            <!-- Сверхурочные: итого (красным) и в скобках только часы без дней -->
            <template v-if="col.key === 'overtime_hours'">
              <div class="overtime-total">{{ formatHours(summaryFor(row).overtime_total) }}</div>
              <div class="overtime-hours-only">({{ formatHours(summaryFor(row).overtime_hours) }})</div>
            </template>
            <!-- КДУ — ручные значения из табеля -->
            <template v-else-if="col.unit === 'manual'">
              {{ fmtNum(row[col.key] ?? 0) }}
            </template>
            <template v-else-if="col.unit === 'hours'">
              {{ formatHours(summaryFor(row)[col.key]) }}
            </template>
            <template v-else>
              {{ summaryFor(row)[col.key] || 0 }}
            </template>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Подписи внизу -->
    <div class="t13-signatures">
      <div class="signature-block">
        <div class="signature-label">Начальник участка заготовок и комплектации изделий</div>
        <div class="signature-line">_____________</div>
        <div class="signature-name">В.Г. Шпакова</div>
      </div>

      <div class="signature-block">
        <div class="signature-label">Начальник отдела кадров</div>
        <div class="signature-line">_____________</div>
        <div class="signature-name">Н.Д. Бубнова</div>
      </div>

      <div class="signature-block">
        <div class="signature-label">Специалист по безопасности</div>
        <div class="signature-line">_____________</div>
        <div class="signature-name">Д.И. Скриган</div>
      </div>
    </div>

    <!-- Кнопка печати (не выводится на бумаге) -->
    <div class="no-print" style="margin-top: 20px; text-align: center;">
      <v-btn color="primary" prepend-icon="mdi-printer" @click="printTable">
        Распечатать
      </v-btn>
      <v-btn variant="outlined" class="ml-2" @click="$router.back()">
        Назад
      </v-btn>
    </div>
  </div>
  <div v-else class="t13-loading">
    <v-progress-circular indeterminate color="primary" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import {
  summaryColumns, calculateSummary, formatHours, fmtNum, getCellHours, getCellCode,
  dayOfWeekNames, MONTH_NAMES_RU
} from '../utils/tabelCalculations'

const route = useRoute()
const tabel = ref(null)
const timeCodes = ref([])

const monthName = computed(() => {
  if (!tabel.value) return ''
  return (MONTH_NAMES_RU[tabel.value.month - 1] || '').toLowerCase()
})

// Реквизиты шапки «УТВЕРЖДАЮ» — из настроек предприятия (если заданы),
// иначе нейтральные значения по умолчанию.
const settings = ref({})
const companyName = computed(() => settings.value.company_name || 'ООО "ПОЛСПО"')
const directorName = computed(() => settings.value.director_name || 'Д.Г. Щербицкий')
const directorPosition = computed(() => settings.value.director_position || 'Генеральный директор')

const weekendSet = computed(() => new Set(tabel.value?.weekend_days || []))
const holidaySet = computed(() => new Set(tabel.value?.holiday_days || []))
function isWeekend(d) { return weekendSet.value.has(d) }
function isHoliday(d) { return holidaySet.value.has(d) }

function getDayOfWeekShort(d) {
  if (!tabel.value) return ''
  const date = new Date(tabel.value.year, tabel.value.month - 1, d)
  return dayOfWeekNames[date.getDay()]
}

// Кэш итогов по строке — расчёт через ОБЩИЙ МОДУЛЬ (идентичен TabelFill.vue),
// поэтому итоги в печати совпадают с табелем заполнения.
const summaryCache = new WeakMap()
function summaryFor(row) {
  let s = summaryCache.get(row)
  if (!s) {
    s = calculateSummary(row, tabel.value, timeCodes.value)
    summaryCache.set(row, s)
  }
  return s
}

async function loadTabel() {
  const id = route.params.id
  try {
    const { data } = await api.get(`/tabels/${id}`)
    tabel.value = data
  } catch (e) {
    console.error('Ошибка загрузки табеля:', e)
    return
  }

  // Коды рабочего времени справочника — нужны для расчёта итогов
  try {
    const { data: codes } = await api.get('/time-codes/')
    timeCodes.value = Array.isArray(codes) ? codes : []
  } catch (e) {
    console.error('Ошибка загрузки кодов:', e)
  }

  // Настройки предприятия — реквизиты шапки (не критично при ошибке)
  try {
    const { data } = await api.get('/company-settings/')
    settings.value = data || {}
  } catch (e) {
    /* используем значения по умолчанию */
  }
}

function printTable() {
  window.print()
}

onMounted(loadTabel)
</script>

<style scoped>
.t13-page {
  padding: 10mm;
  background: white;
  color: #000;
  font-family: 'Times New Roman', Times, serif;
}

.t13-loading {
  display: flex;
  justify-content: center;
  padding: 40px;
}

/* ===== Шапка УТВЕРЖДАЮ ===== */
.t13-approve {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.approve-right {
  text-align: left;
  font-size: 11px;
}

.approve-label {
  font-weight: bold;
  margin-bottom: 5px;
}

.approve-position,
.approve-company {
  margin-bottom: 3px;
}

.approve-sign {
  margin-top: 10px;
  margin-bottom: 5px;
}

.approve-date {
  font-size: 10px;
}

/* ===== Заголовок ===== */
.t13-header {
  text-align: center;
  margin-bottom: 15px;
}

.t13-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 8px;
}

.t13-subtitle {
  font-size: 12px;
  font-weight: normal;
  margin-bottom: 15px;
}

/* ===== Таблица ===== */
.t13-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8px;
}

.t13-table th,
.t13-table td {
  border: 1px solid #000;
  padding: 1px;
  text-align: center;
  vertical-align: middle;
}

.col-num {
  width: 20px;
  min-width: 20px;
  font-size: 8px;
}

.col-fio {
  width: 110px;
  min-width: 110px;
  text-align: left;
  padding-left: 3px;
  font-size: 8px;
}

.col-tabno {
  width: 40px;
  min-width: 40px;
  font-size: 7px;
}

.col-days-header {
  font-weight: bold;
  font-size: 9px;
}

.col-day-header {
  width: 24px;
  min-width: 24px;
  font-size: 6px;
  line-height: 1.1;
}

.day-name {
  font-size: 6px;
  font-weight: normal;
  color: #666;
}

.day-number {
  font-size: 7px;
  font-weight: bold;
}

/* Ячейка дня: ДВЕ строки — код сверху, часы снизу */
.col-day-cell {
  width: 24px;
  min-width: 24px;
  padding: 0;
}

.day-code {
  font-size: 8px;
  font-weight: bold;
  line-height: 1.2;
}

.day-hours {
  font-size: 7px;
  line-height: 1.2;
  color: #333;
}

/* Подсветка: выходные — серый, праздники — жёлтый */
.cell-weekend {
  background-color: #f0f0f0;
}

.cell-holiday {
  background-color: #fff3cd;
}

/* Итоговые колонки: вертикальные заголовки, кроме сверхурочных */
.col-summary-header {
  width: 40px;
  min-width: 40px;
  font-size: 7px;
  font-weight: bold;
  line-height: 1.2;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  transform: rotate(180deg);
  white-space: nowrap;
}

.col-overtime {
  width: 96px !important;
  min-width: 96px !important;
  max-width: 96px !important;
  writing-mode: horizontal-tb !important;
  transform: none !important;
  white-space: normal !important;
}

.col-overtime .ot-main {
  display: block;
  font-weight: bold;
}

.col-overtime .ot-sub {
  display: block;
  font-size: 6px;
  color: #666;
  font-weight: normal;
}

.col-summary-cell {
  font-size: 8px;
  font-weight: normal;
  width: 40px;
  min-width: 40px;
}

.col-overtime-cell {
  width: 96px !important;
  min-width: 96px !important;
  max-width: 96px !important;
}

.overtime-total {
  font-weight: bold;
  color: #d32f2f;
  font-size: 9px;
}

.overtime-hours-only {
  font-size: 7px;
  color: #666;
}

/* ===== Подписи ===== */
.t13-signatures {
  margin-top: 30px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.signature-block {
  flex: 1;
}

.signature-label {
  font-size: 10px;
  font-weight: bold;
  margin-bottom: 20px;
}

.signature-line {
  font-size: 10px;
}

.signature-name {
  font-size: 10px;
}

/* ===== Печать ===== */
@media print {
  @page {
    size: A4 landscape;
    margin: 8mm;
  }

  body {
    margin: 0;
    padding: 0;
  }

  .no-print {
    display: none !important;
  }

  .t13-page {
    padding: 0;
  }

  .t13-table {
    font-size: 7px;
  }

  .t13-table th,
  .t13-table td {
    padding: 0.5px;
  }
}
</style>
