// Быстрый тест расчёта итоговых колонок (NODE: node test-summary.mjs)
import { calculateSummary } from './src/utils/tabelCalculations.js'

const timeCodes = [
  { code: 'О', name: 'Отпуск', hours_day: 0, hours_night: 0, destinations: [] },
  { code: 'В', name: 'Выходной', hours_day: 0, hours_night: 0, destinations: [] },
  { code: 'Б', name: 'Болезнь', hours_day: 0, hours_night: 0, destinations: [] },
  { code: '8ч15м', name: 'Явка', hours_day: 8.25, hours_night: 0, destinations: ['fact_days', 'total_hours', 'tariff_hours'] },
]

const tabel = { days_in_month: 5, weekend_days: [], holiday_days: [] }
const row = {
  employee_id: 1,
  norm_hours: 8,
  day_norms: { 1: 8.25, 2: 8.25, 3: 8.25, 4: 0, 5: 0 },
  days: { 1: '8ч15м', 2: '8ч15м', 3: 'О', 4: 'В', 5: 'Б' },
}

const s = calculateSummary(row, tabel, timeCodes)
console.log('Итоги:', s)

// Ожидаем: фактические дни=2, итого часов=16.5, отпуск=1, болезнь=1, выходные=1
if (s.fact_days !== 2) throw new Error(`fact_days=${s.fact_days}, ожидалось 2`)
if (Math.abs(s.total_hours - 16.5) > 0.01) throw new Error(`total_hours=${s.total_hours}, ожидалось 16.5`)
if (s.vacation !== 1) throw new Error(`vacation=${s.vacation}, ожидалось 1`)
if (s.sick !== 1) throw new Error(`sick=${s.sick}, ожидалось 1`)
if (s.weekend_holiday !== 1) throw new Error(`weekend_holiday=${s.weekend_holiday}, ожидалось 1`)
console.log('OK — все проверки пройдены')
