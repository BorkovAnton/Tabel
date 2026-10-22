// Общие функции расчёта итогов табеля
// Используется в TabelFill.vue и TabelPrint.vue — чтобы итоги в печатной
// форме Т-13 РБ ТОЧНО совпадали с тем, что видит пользователь в табеле.

export const MONTH_NAMES_RU_GENITIVE = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

export const MONTH_NAMES_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

export const DAY_NAMES_RU_FULL = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

export const dayOfWeekNames = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

// Итоговые колонки — ТОЧНО КАК В TABELFILL.VUE
// Колонка «Итого часов» намеренно НЕ последняя: после неё идут остальные
// итоговые колонки, а самой правой является «Часы по тарифу».
// Колонка overtime_hours показывает два значения — «итого» (сверхурочные часы
// + сверхурочные дни × норма дня) и в скобках только часы без учёта дней.
export const summaryColumns = [
  { key: 'fact_days', label: 'фактической работы', unit: 'days' },
  { key: 'total_hours', label: 'Итого часов', unit: 'hours' },
  { key: 'vacation', label: 'трудовой отпуск', unit: 'days' },
  { key: 'sick', label: 'болезнь', unit: 'days' },
  { key: 'admin_leave', label: 'с разрешения администрации', unit: 'days' },
  { key: 'weekend_holiday', label: 'выходные и праздн.', unit: 'days' },
  { key: 'other_absence', label: 'Другие неявки', unit: 'days' },
  { key: 'overtime_days', label: 'сверхурочные дни', unit: 'days' },
  { key: 'overtime_hours', label: 'Сверхурочные часы итого (Сверхурочные часы без дней)', unit: 'hours' },
  { key: 'night_hours', label: 'ночные часы', unit: 'hours' },
  { key: 'kdu_work_days', label: 'КДУ', unit: 'manual' },
  { key: 'kdu_weekend_days', label: 'КДУ вых. дня', unit: 'manual' },
  // Итоговая колонка «по тарифу» — крайняя справа
  { key: 'tariff_hours', label: 'Часы по тарифу', unit: 'hours' }
]

// Форматирование часов: 8.5 → «8ч30м», 21 → «21ч», 0 → «0ч»
export function formatHours(hours) {
  const v = Math.round((Number(hours) || 0) * 60) / 60
  if (!v) return '0ч'
  const h = Math.floor(v)
  const m = Math.round((v - h) * 60)
  if (m === 0) return `${h}ч`
  return `${h}ч${m}м`
}

// Число без хвостовых нулей: 8.50 → «8.5», 8 → «8»
export function fmtNum(n) {
  const v = Number(n) || 0
  return String(Number(v.toFixed(2)))
}

// Разбор числового значения ячейки («8.5», «8ч15м», «8:15») в часы
export function rawToHours(s) {
  const str = String(s ?? '').trim().replace(',', '.')
  let m = str.match(/^(\d+(?:\.\d+)?)\s*ч\s*(\d+)?\s*м?$/)
  if (m) return Number(m[1]) + (Number(m[2] || 0) / 60)
  m = str.match(/^(\d+)\s*:\s*(\d+)$/)
  if (m) return Number(m[1]) + Number(m[2]) / 60
  m = str.match(/^(\d+(?:\.\d+)?)$/)
  if (m) return Number(m[1])
  return null
}

// Норма часов для конкретного дня месяца: из графика работы по дню недели.
// Если графика нет — fallback: employees.norm_hours, иначе 8.
export function getDayNorm(row, d) {
  const dn = row && row.day_norms ? row.day_norms[d] : undefined
  if (dn !== undefined && dn !== null) return Number(dn) || 0
  return normOf(row)
}

export function normOf(row) {
  const n = Number(row && row.norm_hours)
  return n > 0 ? n : 8
}

// Эффективные часы кода для конкретного дня.
// Если у кода включено «Время по графику» (use_schedule_hours):
//  - будний день (норма > 0) — часы берутся из нормы графика (пн = 8.25ч и т.п.);
//  - выходной/праздник (норма = 0) — фиксированные weekend_hours из справочника.
// Иначе — фиксированные hours_day/hours_night из справочника.
export function codeHoursForDay(codeObj, row, d, normOverride = null) {
  if (!codeObj) return { day: 0, night: 0, total: 0 }
  if (codeObj.use_schedule_hours) {
    // normOverride — часы из ДОКУМЕНТА; если задано (> 0) — используем его
    // вместо нормы графика. Норму дня берём у самого дня (getDayNorm).
    const ov = Number(normOverride)
    const norm = row ? getDayNorm(row, d) : 8
    if (Number.isFinite(ov) && ov > 0) {
      if (norm <= 0) return { day: 0, night: ov, total: ov }   // событие в выходной → ночь
      return { day: ov, night: 0, total: ov }                  // событие в будни → день
    }
    if (norm <= 0) {
      // Выходной: используем «Часы для выходного дня», если заданы
      const we = Number(codeObj.weekend_hours)
      const weHours = Number.isFinite(we) && we > 0 ? we : 0
      return { day: weHours, night: 0, total: weHours }
    }
    return { day: norm, night: 0, total: norm }
  }
  const day = Number(codeObj.hours_day) || 0
  const night = Number(codeObj.hours_night) || 0
  return { day, night, total: day + night }
}

// Часы для конкретного значения ячейки. Код справочника НЕ считаем
// числовыми часами (например «7» — это Выходной); возвращает null.
export function cellHoursForDay(timeCodes, val) {
  const s = String(val ?? '').trim()
  if (!s) return null
  const codeObj = timeCodes.find(c => c.code.toLowerCase() === s.toLowerCase())
  if (codeObj) return null
  return rawToHours(s)
}

// Minutes-парсер значения ячейки (число / «8ч15м» / «8:15» / код справочника)
export function cellMinutes(timeCodes, v, row, d) {
  const s = String(v ?? '').trim().toLowerCase().replace(/,/g, '.')
  if (!s) return 0
  let m = s.match(/^(\d+)\s*ч\s*(\d+)?\s*м?$/)
  if (m) return parseInt(m[1]) * 60 + (m[2] ? parseInt(m[2]) : 0)
  m = s.match(/^(\d+)\s*м$/)
  if (m) return parseInt(m[1])
  m = s.match(/^(\d+):([0-5]\d)$/)
  if (m) return parseInt(m[1]) * 60 + parseInt(m[2])
  if (/^\d+(\.\d+)?$/.test(s)) return Math.round(parseFloat(s) * 60)
  const c = timeCodes.find(x => x.code.toLowerCase() === s)
  if (c) {
    // «Время по графику»: часы = норма графика на этот день (если есть контекст дня)
    if (c.use_schedule_hours && row && d) return Math.round(codeHoursForDay(c, row, d).total * 60)
    return Math.round(((Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)) * 60)
  }
  return 0
}

// Суммарные часы строки в формате «NчMм»
export function totalHours(timeCodes, row, daysInMonth) {
  let minutes = 0
  for (let d = 1; d <= daysInMonth; d++) {
    minutes += cellMinutes(timeCodes, row.days[d], row, d)
  }
  const hh = Math.floor(minutes / 60)
  const mm = minutes % 60
  return mm ? `${hh}ч${mm}м` : `${hh}ч`
}

// ГЛАВНАЯ ФУНКЦИЯ: расчёт итогов для строки сотрудника.
// Идентична функции из TabelFill.vue (unit === 'manual' — КДУ — не считается,
// заполняется вручную). Часы сверх нормы автоматически уходят в сверхурочные:
// «Итого часов» = все часы; «по тарифу» = только обычные; превышение — в overtime_*.
export function calculateSummary(row, tabel, timeCodes) {
  const summary = {}
  summaryColumns.forEach(col => { if (col.unit !== 'manual') summary[col.key] = 0 })

  for (let d = 1; d <= tabel.days_in_month; d++) {
    const val = String(row.days[d] || '').trim()
    if (!val) continue

    // Норма по графику работы для этого дня недели (fallback: norm_hours или 8)
    const norm = getDayNorm(row, d)

    const hours = cellHoursForDay(timeCodes, val)
    if (hours !== null && hours > 0) {
      // числовой ввод: обычные часы + сверхурочные сверх нормы по графику.
      // «Сверхурочные дни» при числовом вводе НЕ добавляются.
      const regular = Math.min(hours, norm)
      const ot = Math.max(0, hours - norm)
      summary.total_hours += hours
      summary.fact_days += 1
      summary.tariff_hours += regular
      if (ot > 0) {
        summary.overtime_hours += ot
      }
      continue
    }

    const codeObj = timeCodes.find(c => c.code.toLowerCase() === val.toLowerCase())
    if (codeObj) {
      // «Время по графику»: часы кода = норма графика на этот день (см. codeHoursForDay)
      const eff = codeHoursForDay(codeObj, row, d)
      const hoursDay = eff.day
      const hoursNight = eff.night
      const totalHoursE = eff.total
      const dests = codeObj.destinations || []

      dests.forEach(dest => {
        const colDef = summaryColumns.find(c => c.key === dest)
        if (colDef && Object.prototype.hasOwnProperty.call(summary, dest)) {
          if (colDef.unit === 'days') {
            summary[dest] += 1
          } else if (dest === 'night_hours') {
            summary[dest] += hoursNight
          } else if (dest === 'day_hours') {
            summary[dest] += hoursDay
          } else if (dest === 'overtime_hours') {
            // код с направлением overtime_hours — сверхурочный: ВСЕ его часы
            // идут в «Сверхурочные часы», а не только превышение над нормой.
            summary[dest] += totalHoursE
          } else {
            summary[dest] += totalHoursE
          }
        }
      })

      // Логика сверхурочных ЧАСОВ и ДНЕЙ разделена:
      // - коды с направлением overtime_hours уже добавили ВСЕ свои часы выше;
      // - «Время по графику» + выходные часы: работа в законный выходной
      //   (норма = 0) — ВСЕ эти часы считаются сверхурочными;
      // - обычный код: сверхурочные = превышение фактических часов над нормой.
      const isOvertimeCode = dests.includes('overtime_hours') || dests.includes('overtime_days')
      if (codeObj.use_schedule_hours && !isOvertimeCode && norm <= 0 && totalHoursE > 0) {
        summary.overtime_hours += totalHoursE
      } else if (totalHoursE > 0 && !isOvertimeCode && !codeObj.use_schedule_hours) {
        const ot = Math.max(0, totalHoursE - norm)
        if (ot > 0) {
          summary.overtime_hours += ot
          // из колонок обычных часов вычитаем превышение, если код туда попал
          if (dests.includes('tariff_hours')) summary.tariff_hours = Math.max(0, summary.tariff_hours - ot)
          // «Итого часов» остаётся полным (все введённые часы)
        }
      }
    }
  }

  // Сверхурочные ДНИ тоже считаются сверхурочной работой:
  // 1 день = норма часов этого дня (из графика; fallback norm_hours/8).
  // Итого = сверхурочные часы + Σ(дни × норма); overtime_hours — «часы без дней».
  let otDaysHours = 0
  for (let d = 1; d <= tabel.days_in_month; d++) {
    const val = String(row.days[d] || '').trim().toLowerCase()
    if (!val) continue
    const codeObj = timeCodes.find(c => String(c.code).trim().toLowerCase() === val)
    if (codeObj && (codeObj.destinations || []).includes('overtime_days')) {
      const n = getDayNorm(row, d)
      otDaysHours += n > 0 ? n : (normOf(row) > 0 ? normOf(row) : 8)
    }
  }
  summary.overtime_total = Math.round((summary.overtime_hours + otDaysHours) * 100) / 100

  // Округление на основе типа единицы измерения
  for (const key in summary) {
    const colDef = summaryColumns.find(c => c.key === key)
    if (colDef) {
      if (colDef.unit === 'hours') {
        summary[key] = Math.round(summary[key] * 100) / 100
      } else {
        summary[key] = Math.round(summary[key]) // Дни всегда целые
      }
    }
  }

  return summary
}

// ===== Вспомогательные функции для печатной формы Т-13 =====

// Верхняя строка ячейки дня: сам код/значение («8», «8а», «В», «О», «Б»)
export function getCellCode(val) {
  return val || ''
}

// Нижняя строка ячейка дня: часы. Для кода справочника — эффективные часы
// (по графику/фиксированные), для числового ввода — само значение.
export function getCellHours(val, row, d, timeCodes) {
  if (!val) return ''
  const s = String(val).trim()
  const codeObj = timeCodes.find(c => c.code.toLowerCase() === s.toLowerCase())
  if (codeObj) {
    const eff = codeHoursForDay(codeObj, row, d)
    return eff.total > 0 ? fmtNum(eff.total) : ''
  }
  // Числовое значение
  return s
}
