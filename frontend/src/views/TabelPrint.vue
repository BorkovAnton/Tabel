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
          <th v-for="col in printColumns" :key="col.key" rowspan="2" class="col-summary-header"
              :style="{ width: (col.width || 30) + 'px', minWidth: (col.width || 30) + 'px', maxWidth: (col.width || 30) + 'px' }">
            {{ col.label }}
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
          <td class="col-fio">{{ formatShortName(row.full_name) }}</td>
          <td class="col-tabno">{{ row.tab_number || '—' }}</td>

          <!-- Дни месяца: ЧАСЫ (8.25) если определены, иначе код (К, В, О) -->
          <td v-for="d in tabel.days_in_month" :key="d" class="col-day-cell"
              :class="{ 'cell-weekend': isWeekend(d), 'cell-holiday': isHoliday(d) }">
            <div class="day-hours-only">{{ getCellHours(row.days[d], row, d, timeCodes) }}</div>
          </td>

          <!-- Итоговые колонки — ТОЧНО КАК В ТАБЕЛЕ ЗАПОЛНЕНИЯ (общий модуль tabelCalculations).
               Сверхурочные — две независимые колонки: overtime_total и overtime_hours -->
          <td v-for="col in printColumns" :key="col.key" class="col-summary-cell"
              :style="{ width: (col.width || 30) + 'px', minWidth: (col.width || 30) + 'px', maxWidth: (col.width || 30) + 'px' }">
            {{ summaryCellText(col, row) }}
          </td>
        </tr>
        <!-- Строка «ИТОГО» по отделу — суммирует все строки, как принято в Т-13 -->
        <tr v-if="tabel.entries.length" class="t13-total-row">
          <td :colspan="3 + tabel.days_in_month" class="col-total-label">ИТОГО</td>
          <td v-for="col in printColumns" :key="'tot-' + col.key" class="col-summary-cell"
              :style="{ width: (col.width || 30) + 'px', minWidth: (col.width || 30) + 'px', maxWidth: (col.width || 30) + 'px' }">
            {{ totalsCellText(col) }}
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
      <v-btn color="primary" prepend-icon="mdi-printer" @click="onPrintClick">
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
  summaryColumns, calculateSummary, formatHours, fmtNum, getCellHours,
  dayOfWeekNames, MONTH_NAMES_RU, rawToHours, normalizeListResponse,
  formatShortName
} from '../utils/tabelCalculations'

const route = useRoute()
const tabel = ref(null)
const timeCodes = ref([])
const codesLoadError = ref(false)
const loadError = ref('')

// ===== ПЕРСОНАЛЬНЫЕ НАСТРОЙКИ ПЕЧАТИ =====
// Выбранные пользователем итоговые колонки (GET /api/user-print-settings/).
// Пустой список (настройки не загружены/ошибка) — показываются ВСЕ колонки.
const userPrintColumns = ref([])

const printColumns = computed(() => {
  if (!userPrintColumns.value.length) return summaryColumns
  const filtered = summaryColumns.filter(col => userPrintColumns.value.includes(col.key))
  // Защита: если сохранённые настройки не дали ни одной колонки — показать все
  return filtered.length ? filtered : summaryColumns
})

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

// ===== КЛЮЧ ДАННЫХ ДЛЯ РАСЧЁТА ИТОГОВ =====
// Исправление бага «в итоговых столбцах при печати нет расчётов»: раньше
// расчёт запускался ровно ОДИН раз — сразу после первой загрузки данных.
// Если в этот момент справочник «Коды часов» ещё не дошёл (или страница
// открылась до готовности API), все коды в ячейках не распознавались,
// и итоговые колонки оставались пустыми НАВСЕГДА — даже после того, как
// справочник догружался. Теперь ключом служите и данные табеля, и сам
// справочник кодов: как только приходит ЛЮБОЕ из них — итоги пересчитываются.
const calcKey = computed(() => JSON.stringify([
  tabel.value ? {
    y: tabel.value.year, m: tabel.value.month, d: tabel.value.days_in_month,
    w: tabel.value.weekend_days || [], h: tabel.value.holiday_days || [],
    e: (tabel.value.entries || []).map(r => ({
      id: r.employee_id, n: r.norm_hours,
      dn: r.day_norms || {}, k1: r.kdu_work_days, k2: r.kdu_weekend_days,
      days: r.days || {},
    })),
  } : null,
  // нормализованный снимок справочника: код + часы + флаг графика + назначения
  (timeCodes.value || []).map(c => [
    c.code, Number(c.hours_day) || 0, Number(c.hours_night) || 0,
    !!c.use_schedule_hours, Number(c.weekend_hours) || 0,
    (c.destinations || []).join('|'),
  ]),
]))

// Итоги по строкам — расчёт через ОБЩИЙ МОДУЛЬ (идентичен TabelFill.vue),
// поэтому итоги в печати совпадают с табелем заполнения. Пересчитывается
// автоматически при любом изменении calcKey (см. выше).
const summaries = computed(() => {
  void calcKey.value // подписка: пересчёт при смене данных табеля/справочника
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

// ===== ФОРМАТ ИТОГОВ — КАК В ТАБЕЛЕ ЗАПОЛНЕНИЯ (TabelFill.vue) =====
// В табеле заполнения дни выводятся числом, часовые колонки — в формате
// «NчMм» (formatHours), а сверхурочные показывают «итого (только часы)»,
// например «21ч (5ч)». Печать использует те же правила, чтобы значения на
// бумаге совпадали с экраном один-в-один.

// Часы → «21ч» / «8ч30м» / «0ч»
function hoursText(v) {
  return formatHours(v)
}

// Универсальный вывод ячейки итоговой колонки (строка сотрудника).
// Сверхурочные — две обычные независимые колонки (overtime_total / overtime_hours),
// специального рендера больше нет.
function summaryCellText(col, row) {
  const s = summaryOf(row)
  if (col.unit === 'manual') return fmtNum(row[col.key] ?? 0)
  if (col.unit === 'hours') return hoursText(s[col.key])
  // days — просто число, как в табеле заполнения
  return String(Math.round(Number(s[col.key]) || 0))
}

// Универсальный вывод ячейки строки «ИТОГО».
function totalsCellText(col) {
  const t = totals.value
  if (col.unit === 'hours') return hoursText(t[col.key])
  return fmtNum(t[col.key])
}

// Данные ещё грузятся (табель или справочник кодов) — показываем явное
// состояние вместо молчаливых нулей/пустоты в итоговых колонках.
const dataReady = computed(() => !!tabel.value && Array.isArray(tabel.value.entries))
const codesPending = computed(() => dataReady.value && hasCodeValues.value && timeCodes.value.length === 0 && !codesLoadError.value)
const hasCodeValues = computed(() => {
  const t = tabel.value
  if (!t || !Array.isArray(t.entries)) return false
  return t.entries.some(r => Object.values(r.days || {}).some(v => {
    const s = String(v || '').trim()
    return s && rawToHours(s) === null
  }))
})

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

    // ✅ Персональные настройки печати пользователя (какие итоговые колонки
    // показывать). Ошибка/пусто → userPrintColumns остаётся пустым →
    // printColumns покажет ВСЕ колонки (обратная совместимость).
    try {
      const settingsRes = await api.get('/api/user-print-settings/')
      const s = settingsRes && settingsRes.data !== undefined ? settingsRes.data : settingsRes
      userPrintColumns.value = Array.isArray(s.selected_columns) ? s.selected_columns : []
    } catch (e) {
      console.error('Ошибка загрузки настроек печати:', e)
      userPrintColumns.value = []  // Показать все колонки
    }
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

// ===== ПЕЧАТЬ В НОВОМ ОКНЕ — РЕШЕНИЕ «В ИТОГОВЫХ СТОЛБЦАХ ПРИ ПЕЧАТИ НЕТ РАСЧЁТОВ» =====
// Браузер строит предпросмотр печати из ДОКУМЕНТА, в котором вызван print().
// Если печать вызывается на другой странице (например, пользователь нажал
// Ctrl+P, находясь ещё на табеле заполнения), печатается тот DOM — и в нём
// расчётов нет. Поэтому кнопка «Распечатать» открывает новое окно, полностью
// копирует в него ОТОБРАЖЁННУЮ таблицу (уже с посчитанными итогами), ждёт
// загрузки стилей и вызывает print() внутри нового документа — там всегда
// актуальные расчёты. Старое окно остаётся фоном для системного Ctrl+P.
let printWin = null

async function openPrintWindow() {
  await nextTick()
  const node = document.querySelector('.t13-page')
  if (!node) return false
  const win = window.open('', '_blank', 'width=1400,height=900')
  if (!win) return false // браузер заблокировал всплывающее окно
  printWin = win
  const styles = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
    .map(n => n.outerHTML).join('\n')
  const html = node.cloneNode(true)
  const noPrintEls = html.querySelectorAll('.no-print')
  for (const el of noPrintEls) el.parentNode.removeChild(el)
  win.document.open()
  win.document.write(
    '<!doctype html><html lang="ru"><head><meta charset="utf-8">' +
    '<title>Табель Т-13 — печать</title>' + styles + '</head><body>' +
    html.outerHTML + '</body></html>'
  )
  win.document.close()
  // даём новому окну применить стили и отрисовать таблицы перед диалогом печати
  await new Promise(res => setTimeout(res, 350))
  try { win.focus() } catch (e) { /* noop */ }
  win.print()
  return true
}

async function onPrintClick() {
  if (printing) return
  printing = true
  try {
    await loadTabel()          // свежие данные + справочник кодов
    await nextTick()           // Vue пересчитает итоги (summaries/totals)
    const ok = await openPrintWindow()
    if (!ok) {
      // fallback: печать текущего окна после полной перерисовки
      await nextTick()
      window.print()
    }
  } finally {
    printing = false
  }
}

const onBeforePrint = () => {
  // beforeprint синхронный и не даёт дождаться асинхронного расчёта, но если
  // данные уже загружены — итоги в текущем документе актуальны; дополнительно
  // запускаем обновление на случай «печатают прямо из-под Ctrl+P».
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

/* ===== Заголовок (компактный) ===== */
.t13-header {
  text-align: center;
  margin-bottom: 10px;         /* Уменьшили с 15px */
}

.t13-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 5px;          /* Уменьшили с 8px */
}

.t13-subtitle {
  font-size: 12px;
  font-weight: normal;
  margin-bottom: 10px;         /* Уменьшили с 15px */
}

/* ===== Таблица (единый шрифт 13px, максимально компактная: без отступов) ===== */
.t13-table {
  width: 100%;
  border-collapse: collapse;
  /* auto вместо fixed: колонка ФИО («процентная» колонка) автоматически
     растягивается под самое длинное содержимое — ФИО всегда в одну строку.
     Колонки дней и итоговые имеют фиксированные ширины (см. CSS/:style),
     поэтому раскладка остаётся стабильной и компактной. */
  table-layout: auto;
  font-size: 13px !important;  /* ЕДИНЫЙ РАЗМЕР ШРИФТА для всей таблицы */
  line-height: 0.9 !important; /* Минимальная высота строки */
}

.t13-table th,
.t13-table td {
  border: 1px solid #000;
  padding: 0 !important;       /* Убрали padding полностью */
  margin: 0 !important;
  text-align: center;
  vertical-align: middle;
  line-height: 0.9 !important; /* Минимальная высота строки */
}

.col-num {
  width: 20px !important;      /* Сузили с 25px */
  min-width: 20px !important;
  max-width: 20px !important;
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  font-weight: bold;
  padding: 0 !important;
  line-height: 0.9 !important;
}

.col-fio {
  /* Адаптивная ширина: колонка занимает всё свободное место таблицы
     (все остальные колонки зафиксированы), поэтому ФИО гарантированно
     помещается в одну строку без обрезки и переносов */
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  white-space: nowrap;         /* Запрет переноса ФИО на новую строку */
  overflow-wrap: normal;       /* Никаких разрывов длинных слов */
  word-break: normal;
  text-overflow: clip;         /* Обрезка не происходит — колонка адаптивна */
  text-align: left;
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  font-weight: 500;
  padding: 0 2px !important;   /* Небольшой горизонтальный отступ для читаемости */
  line-height: 0.9 !important;
}

.col-tabno {
  width: 35px !important;      /* Сузили с 40px */
  min-width: 35px !important;
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  padding: 0 !important;
  line-height: 0.9 !important;
}

.col-days-header {
  font-weight: bold;
  font-size: 13px;             /* Единый размер шрифта 13px */
}

.col-day-header {
  width: 26px !important;      /* Сузили с 28px */
  min-width: 26px !important;
  max-width: 26px !important;
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  line-height: 0.9 !important; /* Минимальная высота */
  padding: 0 !important;       /* Убрали padding */
  height: auto !important;     /* Убрали фиксированную высоту */
  margin: 0 !important;
}

.day-name {
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  font-weight: 600;
  color: #666;
  line-height: 0.9 !important;
  padding: 0 !important;
  margin: 0 !important;
}

.day-number {
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  font-weight: bold;
  line-height: 0.9 !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* Ячейка дня: ЧАСЫ (8.25) если есть, иначе код (К, В, О) — компактно, текст плотно к границам */
.col-day-cell {
  width: 26px !important;      /* Сузили с 28px */
  min-width: 26px !important;
  max-width: 26px !important;
  padding: 0 !important;       /* Убрали padding полностью */
  margin: 0 !important;
  height: auto !important;     /* Убрали фиксированную высоту */
  line-height: 0.9 !important; /* Минимальная высота строки */
}

.day-hours-only {
  font-size: 13px !important;  /* Уменьшили с 14px */
  font-weight: bold;
  line-height: 0.9 !important; /* Минимальная высота строки */
  color: #000;
  text-align: center;
  padding: 0 !important;       /* Убрали padding */
  margin: 0 !important;        /* Убрали margin */
  display: block;
  word-break: break-all;       /* Длинные значения переносятся внутри ячейки */
}

/* Подсветка: выходные — серый, праздники — жёлтый */
.cell-weekend {
  background-color: #f0f0f0;
}

.cell-holiday {
  background-color: #fff3cd;
}

/* Выходные и праздники — такой же компактный крупный шрифт */
.cell-weekend .day-hours-only,
.cell-holiday .day-hours-only {
  font-size: 13px !important;
  font-weight: bold;
}

/* Итоговые колонки: ВСЕ вертикальные, единый шрифт 13px.
   Ширина задаётся через inline :style из col.width («Итого часов» — 45px,
   остальные — 30px), здесь только fallback min-width */
.col-summary-header {
  min-width: 28px !important;
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  font-weight: bold;
  line-height: 0.9 !important;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  transform: rotate(180deg);
  white-space: nowrap;
  padding: 0 !important;       /* Убрали padding */
}

/* Сверхурочные разделены на две обычные независимые итоговые колонки
   (overtime_total и overtime_hours) — специальные стили .col-overtime /
   .overtime-total / .overtime-hours-only больше не нужны */

.col-summary-cell {
  font-size: 13px !important;  /* Единый размер шрифта 13px */
  font-weight: 500;
  min-width: 28px !important;  /* Ширина — через inline :style из col.width */
  padding: 0 !important;       /* Убрали padding */
  line-height: 0.9 !important;
}

/* Строка ИТОГО */
.t13-total-row td {
  font-weight: bold;
  background-color: #f7f7f7;
}

.col-total-label {
  text-align: right;
  padding-right: 6px !important;
  font-size: 13px;             /* Единый размер шрифта 13px */
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

/* ===== Подписи (компактные) ===== */
.t13-signatures {
  margin-top: 15px;            /* Уменьшили с 30px */
  display: flex;
  justify-content: space-between;
  gap: 10px;                   /* Уменьшили с 20px */
}

.signature-block {
  flex: 1;
}

.signature-label {
  font-size: 10px;
  font-weight: bold;
  margin-bottom: 10px;         /* Уменьшили с 20px */
}

.signature-line {
  font-size: 10px;
}

.signature-name {
  font-size: 10px;
}

/* ===== Печать ===== */
@media print {
  /* A3 landscape — шире, вмещает все колонки; минимальные поля для компактности */
  @page {
    size: A3 landscape;
    margin: 2mm;               /* Уменьшили с 3mm до 2mm */
  }

  body {
    margin: 0;
    padding: 0;
    font-size: 13px;           /* Единый размер шрифта 13px */
    line-height: 0.9;
  }

  .no-print {
    display: none !important;
  }

  .t13-page {
    padding: 0;
    width: 100%;
  }

  .t13-table {
    font-size: 13px !important;  /* ЕДИНЫЙ РАЗМЕР при печати */
    line-height: 0.9 !important;
  }

  .t13-table th,
  .t13-table td {
    padding: 0 !important;     /* Без отступов при печати */
    line-height: 0.9 !important;
  }

  /* ФИО — адаптивная ширина и одна строка при печати */
  .col-fio {
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
    white-space: nowrap !important;
    overflow-wrap: normal !important;
    word-break: normal !important;
    padding: 0 2px !important;
  }

  /* Сохранить фоновые цвета ячеек при печати */
  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  /* Печать только формы Т-13: скрываем всё остальное на странице
     (навигация сайта, кнопки) — иначе в предпросмотре вместо расчётов
     печатается чужой DOM. */
  body * {
    visibility: hidden;
  }
  .t13-page,
  .t13-page * {
    visibility: visible;
  }
  .t13-page {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
  }
}
</style>
