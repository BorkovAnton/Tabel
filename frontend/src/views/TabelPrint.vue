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
              <div class="overtime-total">{{ formatHours(summaryOf(row).overtime_total) }}</div>
              <div class="overtime-hours-only">({{ formatHours(summaryOf(row).overtime_hours) }})</div>
            </template>
            <!-- КДУ — ручные значения из табеля -->
            <template v-else-if="col.unit === 'manual'">
              {{ fmtNum(row[col.key] ?? 0) }}
            </template>
            <template v-else-if="col.unit === 'hours'">
              {{ formatHours(summaryOf(row)[col.key]) }}
            </template>
            <template v-else>
              {{ summaryOf(row)[col.key] || 0 }}
            </template>
          </td>
        </tr>
        <!-- Строка «ИТОГО» по отделу — суммирует все строки, как принято в Т-13 -->
        <tr v-if="tabel.entries.length" class="t13-total-row">
          <td :colspan="3 + tabel.days_in_month" class="col-total-label">ИТОГО</td>
          <td v-for="col in summaryColumns" :key="'tot-' + col.key" class="col-summary-cell"
              :class="{ 'col-overtime-cell': col.key === 'overtime_hours' }">
            <template v-if="col.key === 'overtime_hours'">
              <div class="overtime-total">{{ formatHours(totals.overtime_total) }}</div>
              <div class="overtime-hours-only">({{ formatHours(totals.overtime_hours) }})</div>
            </template>
            <template v-else-if="col.unit === 'hours'">
              {{ formatHours(totals[col.key]) }}
            </template>
            <template v-else>
              {{ fmtNum(totals[col.key]) }}
            </template>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Итоги НЕ рассчитались (например, не загрузился справочник кодов) -->
    <div v-if="showCalcWarning" class="no-print calc-warning">
      ⚠ Не удалось рассчитать итоги (не загружен справочник «Коды часов»).
      Проверьте доступность сервера и обновите страницу.
    </div>

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
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import {
  summaryColumns, calculateSummary, formatHours, fmtNum, getCellHours, getCellCode,
  dayOfWeekNames, MONTH_NAMES_RU, rawToHours, normalizeListResponse
} from '../utils/tabelCalculations'

const route = useRoute()
const tabel = ref(null)
const timeCodes = ref([])
const codesLoadError = ref(false)
const loadError = ref('')

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

// Итоги по строкам — расчёт через ОБЩИЙ МОДУЛЬ (идентичен TabelFill.vue),
// поэтому итоги в печати совпадают с табелем заполнения.
// Реактивная вычисляемая карта (computed): пересчитывается автоматически,
// когда завершится загрузка табеля и справочника кодов (раньше из-за кэша на
// WeakMap, заполненного до загрузки данных, итоговые колонки были пустыми).
const summaries = computed(() => {
  const map = new Map()
  const t = tabel.value
  if (!t || !Array.isArray(t.entries)) return map
  for (const row of t.entries) {
    try {
      map.set(row.employee_id, calculateSummary(row, t, timeCodes.value))
    } catch (e) {
      console.error('Ошибка расчёта итогов для строки:', row && row.employee_id, e)
    }
  }
  return map
})

function summaryOf(row) {
  return summaries.value.get(row.employee_id) || {}
}

// Строка «ИТОГО»: сумма по всем сотрудникам (КДУ — тоже суммируются)
const totals = computed(() => {
  const res = {}
  summaryColumns.forEach(col => { res[col.key] = 0 })
  res.overtime_total = 0
  summaries.value.forEach(s => {
    summaryColumns.forEach(col => {
      // КДУ (unit === 'manual') не входят в summary — добавляются ниже из строк
      if (col.unit === 'manual') return
      res[col.key] += Number(s[col.key]) || 0
    })
    res.overtime_total += Number(s.overtime_total) || 0
  })
  // КДУ хранятся в строке (ручной ввод), не в summary
  if (tabel.value && Array.isArray(tabel.value.entries)) {
    for (const row of tabel.value.entries) {
      res.kdu_work_days += Number(row.kdu_work_days) || 0
      res.kdu_weekend_days += Number(row.kdu_weekend_days) || 0
    }
  }
  // округление
  summaryColumns.forEach(col => {
    res[col.key] = col.unit === 'hours' || col.unit === 'manual'
      ? Math.round(res[col.key] * 100) / 100
      : Math.round(res[col.key])
  })
  res.overtime_total = Math.round(res.overtime_total * 100) / 100
  return res
})

// Предупреждение, если в табеле есть данные, но ни один код не распознан
// (пустой/недогруженный справочник) — иначе пользователь видит «пустые» итоги
// и думает, что расчётов нет.
const showCalcWarning = computed(() => {
  const t = tabel.value
  if (!t || !Array.isArray(t.entries) || !t.entries.length) return false
  if (codesLoadError.value) return true
  const hasAnyValue = t.entries.some(r => Object.values(r.days || {}).some(v => String(v || '').trim()))
  const hasAnyNonNumeric = t.entries.some(r =>
    Object.values(r.days || {}).some(v => {
      const s = String(v || '').trim()
      return s && rawToHours(s) === null
    })
  )
  return hasAnyValue && hasAnyNonNumeric && timeCodes.value.length === 0
})

async function loadTabel() {
  // Табель и справочник кодов грузятся ПАРАЛЛЕЛЬНО и оба до конца, прежде чем
  // что-либо отобразится. Раньше табель мог отрисоваться раньше кодов — итоги
  // считались с пустым справочником и в печатной форме выходили пустыми.
  const raw = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const id = Number(raw)
  if (!Number.isInteger(id) || id <= 0) {
    console.error('Некорректный id табеля в URL:', raw)
    return
  }
  let tabelData = null
  try {
    const [tabelRes, codesRes] = await Promise.all([
      api.get(`/tabels/${id}`),
      api.get('/time-codes/').catch(e => {
        console.error('Ошибка загрузки справочника кодов часов:', e)
        codesLoadError.value = true
        return null
      })
    ])
    tabelData = tabelRes && tabelRes.data ? tabelRes.data : tabelRes
    // ИСПРАВЛЕНО: раньше здесь ожидался «голый» массив; если API возвращал
    // обёртку ({ items: [...] } и т.п.) или ответ уже был развёрнут,
    // timeCodes оставался пустым → ВСЕ итоговые колонки на печати были пусты.
    const codesRaw = codesRes && codesRes.data !== undefined ? codesRes.data : codesRes
    timeCodes.value = normalizeListResponse(codesRaw).filter(c => c && c.code)
  } catch (e) {
    loadError.value = e && e.response && e.response.status === 403
      ? 'У вас нет доступа к этому табелю.'
      : 'Не удалось загрузить данные табеля. Проверьте доступность сервера и обновите страницу.'
    console.error('Ошибка загрузки табеля:', e)
    return
  }

  if (!tabelData) return
  // Defensive: нормализуем структуру данных табеля, чтобы расчёт итогов
  // не падал на отсутствии полей (entries/days/days_in_month).
  if (!Array.isArray(tabelData.entries)) tabelData.entries = []
  for (const row of tabelData.entries) {
    if (!row.days || typeof row.days !== 'object') row.days = {}
  }
  tabel.value = tabelData

  // Настройки предприятия — реквизиты шапки (не критично при ошибке)
  try {
    const res = await api.get('/company-settings/')
    settings.value = (res && res.data) || res || {}
  } catch (e) {
    /* используем значения по умолчанию */
  }
}

function printTable() {
  doPrint()
}

// ===== ГАРАНТИЯ АКТУАЛЬНЫХ ИТОГОВ ПРИ ПЕЧАТИ =====
// Браузер печатает текущий DOM. Если в момент Ctrl+P итоги ещё не досчитаны
// (данные/справочник кодов грузятся асинхронно или открыт системный диалог
// печати до готовности), в итоговых колонках окажутся пустые ячейки.
// Поэтому перед каждой печатью принудительно перезагружаем данные и ждём
// полной перерисовки таблицы, и только потом вызываем window.print().
let printing = false

async function ensureFreshData() {
  try {
    await loadTabel()
  } catch (e) {
    console.error('Не удалось обновить данные перед печатью:', e)
  }
  await nextTick()
}

function doPrint() {
  if (printing) return
  printing = true
  ensureFreshData().finally(() => {
    // двойной nextTick: к этому моменту Vue гарантированно отрисует
    // пересчитанные итоговые значения в DOM
    nextTick(() => nextTick(() => {
      printing = false
      window.print()
    }))
  })
}

const onBeforePrint = (e) => {
  // preventDefault не работает для beforeprint — но это единственный способ
  // перехватить пользовательский Ctrl+P: помечаем событие и после открытия
  // предпросмотра обновляем данные; сам предпросмотр браузер уже построит по
  // текущему DOM, поэтому надёжнее всего печатать через кнопку «Печать Т-13».
  if (!printing) ensureFreshData()
}

const onAfterPrint = () => { printing = false }

watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) loadTabel()
})

onMounted(() => {
  loadTabel()
  window.addEventListener('beforeprint', onBeforePrint)
  window.addEventListener('afterprint', onAfterPrint)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeprint', onBeforePrint)
  window.removeEventListener('afterprint', onAfterPrint)
})
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

/* ===== Таблица (сжатая, чтобы влезла по ширине) ===== */
.t13-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 6px;
}

.t13-table th,
.t13-table td {
  border: 1px solid #000;
  padding: 0.5px;
  text-align: center;
  vertical-align: middle;
  overflow: hidden;
}

.col-num {
  width: 15px;
  min-width: 15px;
  max-width: 15px;
  font-size: 6px;
}

.col-fio {
  width: 70px;
  min-width: 70px;
  text-align: left;
  padding-left: 2px;
  font-size: 6px;
}

.col-tabno {
  width: 28px;
  min-width: 28px;
  font-size: 5px;
}

.col-days-header {
  font-weight: bold;
  font-size: 7px;
}

.col-day-header {
  font-size: 5px;
  line-height: 1.1;
  padding: 0.5px 0 !important;
}

.day-name {
  font-size: 4px;
  font-weight: normal;
  color: #666;
}

.day-number {
  font-size: 5px;
  font-weight: bold;
}

/* Ячейка дня: ДВЕ строки — код сверху, часы снизу */
.col-day-cell {
  padding: 0 !important;
}

.day-code {
  font-size: 6px;
  font-weight: bold;
  line-height: 1.1;
}

.day-hours {
  font-size: 5px;
  line-height: 1.1;
  color: #333;
}

/* Подсветка: выходные — серый, праздники — жёлтый */
.cell-weekend {
  background-color: #f0f0f0;
}

.cell-holiday {
  background-color: #fff3cd;
}

/* Итоговые колонки: ВСЕ вертикальные, включая сверхурочные */
.col-summary-header {
  width: 28px;
  min-width: 28px;
  max-width: 28px;
  font-size: 5px;
  font-weight: bold;
  line-height: 1.1;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  transform: rotate(180deg);
  white-space: nowrap;
  padding: 2px 1px !important;
}

/* Сверхурочные — вертикальная, как все остальные итоговые колонки */
.col-overtime {
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  writing-mode: vertical-rl !important;
  text-orientation: mixed;
  transform: rotate(180deg) !important;
  white-space: nowrap !important;
  font-size: 5px !important;
  line-height: 1.1 !important;
  padding: 2px 1px !important;
}

.col-overtime .ot-main {
  display: inline;
  font-weight: bold;
}

.col-overtime .ot-sub {
  display: inline;
  font-size: 5px !important;
  color: #666;
  font-weight: normal;
}

.col-summary-cell {
  font-size: 6px;
  font-weight: normal;
  width: 28px;
  min-width: 28px;
  max-width: 28px;
}

/* Ячейки тела таблицы для сверхурочных — тоже узкие */
.col-overtime-cell {
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  font-size: 6px !important;
}

.overtime-total {
  font-weight: bold;
  color: #d32f2f;
  font-size: 7px;
  line-height: 1.2;
}

.overtime-hours-only {
  font-size: 5px;
  color: #666;
  line-height: 1.2;
}

/* Строка ИТОГО */
.t13-total-row td {
  font-weight: bold;
  background-color: #f7f7f7;
}

.col-total-label {
  text-align: right;
  padding-right: 6px !important;
  font-size: 8px;
  letter-spacing: 2px;
}

/* Предупреждение о нерассчитанных итогах (только на экране, не при печати) */
.calc-warning {
  margin-top: 10px;
  padding: 8px 12px;
  border: 1px solid #d32f2f;
  border-radius: 4px;
  color: #d32f2f;
  background: #ffebee;
  font-size: 12px;
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
  /* A3 landscape — шире, вмещает все колонки */
  @page {
    size: A3 landscape;
    margin: 5mm;
  }

  body {
    margin: 0;
    padding: 0;
    font-size: 6px;
  }

  .no-print {
    display: none !important;
  }

  .t13-page {
    padding: 0;
    width: 100%;
  }

  .t13-table {
    font-size: 6px !important;
  }

  .t13-table th,
  .t13-table td {
    padding: 0.5px;
  }

  /* Сохранить фоновые цвета ячеек при печати */
  .cell-weekend,
  .cell-holiday,
  .overtime-total {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}
</style>
