// Тесты расчёта сводных колонок по направлениям (destinations) кодов.
// Запуск: node frontend/test-summary-destinations.mjs
import { calculateSummary } from './src/utils/tabelCalculations.js'

let failed = 0
function check(name, actual, expected) {
  const ok = Math.abs((Number(actual) || 0) - (Number(expected) || 0)) < 1e-9
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}: получено ${actual}, ожидалось ${expected}`)
  if (!ok) failed++
}

const tabel = { days_in_month: 30, weekend_days: [], holiday_days: [] }
const mkRow = (days) => ({ employee_id: 1, full_name: 'Тест', norm_hours: 8, day_norms: {}, days })

// Коды из задачи:
// «8ч15м»: направления = [«Фактической работы», «Итого часов»] — тарифа НЕТ
// «8тс» : направления = [«Часы по тарифу», «Итого часов», «сверхурочные дни»]
const codes = [
  { code: '8ч15м', name: '8 часов 15 минут', hours_day: 8.25, hours_night: 0, use_schedule_hours: false, destinations: ['Фактической работы', 'Итого часов'] },
  { code: '8тс', name: '8ч по тарифу в выходной день', hours_day: 8, hours_night: 0, use_schedule_hours: false, destinations: ['Часы по тарифу', 'Итого часов', 'Часы по тарифу', 'сверхурочные дни'] },
  // канонические ключи тоже должны работать
  { code: 'Н', name: 'Ночные', hours_day: 0, hours_night: 4, use_schedule_hours: false, destinations: ['night_hours', 'total_hours'] },
]

// 1) День с «8ч15м»: факт+итого есть, тарифа нет
let s = calculateSummary(mkRow({ 1: '8ч15м' }), tabel, codes)
check('8ч15м → Часы по тарифу = 0 (не было направления)', s.tariff_hours, 0)
check('8ч15м → Итого часов = 8.25', s.total_hours, 8.25)
check('8ч15м → фактической работы = 1 день', s.fact_days, 1)

// 2) День с «8тс»: тариф + итого + сверхурочные дни
s = calculateSummary(mkRow({ 2: '8тс' }), tabel, codes)
check('8тс → Часы по тарифу = 8', s.tariff_hours, 8)
check('8тс → Итого часов = 8', s.total_hours, 8)
check('8тс → сверхурочные дни = 1', s.overtime_days, 1)
check('8тс → Сверхурочные часы итого = 8 (день × норма)', s.overtime_total, 8)

// 3) Оба кода в месяце — суммы корректны, дубликат направления не удваивает
s = calculateSummary(mkRow({ 1: '8ч15м', 2: '8тс' }), tabel, codes)
check('Месяц: Часы по тарифу = 8 (только 8тс)', s.tariff_hours, 8)
check('Месяц: Итого часов = 16.25', s.total_hours, 16.25)
check('Месяц: фактических работы = 2 дня', s.fact_days, 2)

// 4) Код без направления «Итого часов» не попадает в итог
const codesNoTotal = [{ code: 'Т', name: 'Только тариф', hours_day: 5, hours_night: 0, use_schedule_hours: false, destinations: ['Часы по тарифу'] }]
s = calculateSummary(mkRow({ 1: 'Т' }), tabel, codesNoTotal)
check('Код без «Итого часов»: Итого = 0', s.total_hours, 0)
check('Код без «Итого часов»: Тариф = 5', s.tariff_hours, 5)

// 5) Эвристика (пустые destinations) — рабочее поведение НЕ меняется
const codesHeur = [{ code: 'ЯР', name: 'Работа', hours_day: 8, hours_night: 0, use_schedule_hours: false, destinations: [] }]
s = calculateSummary(mkRow({ 1: 'ЯР' }), tabel, codesHeur)
check('Эвристика: Итого = 8', s.total_hours, 8)
check('Эвристика: Тариф = 8', s.tariff_hours, 8)
check('Эвристика: фактических дней = 1', s.fact_days, 1)

// 6) Сверхурочные: код с тарифом 10ч при норме 8 → тариф 8, ОТ 2
const codesOT = [{ code: '10т', name: 'Десять', hours_day: 10, hours_night: 0, use_schedule_hours: false, destinations: ['Часы по тарифу', 'Итого часов'] }]
s = calculateSummary(mkRow({ 1: '10т' }), tabel, codesOT)
check('Сверх нормы: Тариф = 8', s.tariff_hours, 8)
check('Сверх нормы: ОТ часы = 2', s.overtime_hours, 2)
check('Сверх нормы: Итого = 10', s.total_hours, 10)

// 7) Код без тарифного направления и со сверхнормой: тариф остаётся 0
const codesOT2 = [{ code: '10ф', name: 'Десять факт', hours_day: 10, hours_night: 0, use_schedule_hours: false, destinations: ['Фактической работы', 'Итого часов'] }]
s = calculateSummary(mkRow({ 1: '10ф' }), tabel, codesOT2)
check('Без тарифа, сверхнорма: Тариф = 0', s.tariff_hours, 0)
check('Без тарифа, сверхнорма: ОТ часы = 2', s.overtime_hours, 2)

// 8) Ночные часы по каноническому ключу
s = calculateSummary(mkRow({ 1: 'Н' }), tabel, codes)
check('Ночной код: night_hours = 4', s.night_hours, 4)
check('Ночной код: Итого = 4', s.total_hours, 4)
check('Ночной код: Тариф = 0 (нет направления)', s.tariff_hours, 0)

if (failed) { console.error(`\n${failed} проверок ПРОВАЛЕНО`); process.exit(1) }
console.log('\nВсе проверки пройдены')
