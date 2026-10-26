// Общие функции расчёта итогов табеля
// Используется в TabelFill.vue и TabelPrint.vue — чтобы итоги в печатной
// форме Т-13 РБ ТОЧНО совпадали с тем, что видит пользователь в табеле.

export const MONTH_NAMES_RU_GENITIVE = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

export const MONTH_NAMES_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

export const DAY_NAMES_RU_FULL = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

export const dayOfWeekNames = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

// ===== Нормализация ответов API =====
// Axios-перехватчики и разные версии бэкенда могут возвращать ответ либо как
// массив напрямую, либо в обёртке { items: [...] } / { data: [...] }.
// Раньше в печатной форме ожидался «голый» массив; если приходила обёртка —
// справочник кодов оставался пустым и ВСЕ ИТОГОВЫЕ КОЛОНКИ выходили пустыми.
export function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  if (data && Array.isArray(data.data)) return data.data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

// ===== ЭВРИСТИКА ПО НАЗВАНИЮ/КОДУ СПРАВОЧНИКА =====
// ИСПРАВЛЕНИЕ БАГА «при печати не считаются суммирующие колонки, например
// "Отпуск"»: раньше код попадал в суммирующую колонку ТОЛЬКО если у него
// явно заданы destinations. Если справочник заполнен без назначений (в UI
// так и написано — «Не указано»), ВСЕ неявочные коды («Отпуск», «Болезнь»,
// «Выходной», «Неявка») печатались нулями. Теперь для кодов БЕЗ назначений
// колонка определяется по названию (см. NAME_HINTS), а стандартные коды
// табеля Т-13 — по букве кода (см. STANDARD_CODE_HINTS). Явные destinations
// имеют безусловный приоритет — эвристика их НЕ переопределяет.
const NAME_HINTS = [
  // болезнь («болезнь», «больничный», «нетрудоспособность»)
  { key: 'sick', re: /(болезн|больничн|нетрудоспов)/i },
  // трудовой отпуск («отпуск», «очередной», «декрет», «беременность», «учебный»)
  { key: 'vacation', re: /(отпуск|vacation|очередн|декрет|беременн|учебн)/i },
  // отпуск с разрешения администрации («за свой счёт», «административный»)
  { key: 'admin_leave', re: /(разрешени[ею]? админ|административн|за свой счёт|за свой счет|без сохран)/i },
  // выходные и праздники («выходной», «праздник», «нерабочий»)
  { key: 'weekend_holiday', re: /(выходн|праздник|праздн|holiday|weekend|нерабоч)/i },
  // прочие неявки («неявка», «прогул», «отстранение»)
  { key: 'other_absence', re: /(неявк|прогул|отстранен|другие причин|иной причин|предотврат)/i },
]

// Стандартные коды табеля Т-13 РБ (буква кода → колонка). Применяется только
// когда название ничего не подсказало и destinations пусты.
// ВАЖНО: проверка идёт ПОСЛЕДОВАТЕЛЬНО (как в реальном справочнике Т-13):
// «О» — отпуск; «ОД/ОУ/ОБ» — отпуск декретный/учебный/без сохранения —
// тоже отпуск; «ВП» — временная нетрудоспособность (болезнь), а НЕ выходные;
// «ЯР/Я-Р» — с разрешения администрации, проверяется раньше простой «Я».
const STANDARD_CODE_HINTS = [
  { key: 'sick', re: /^(вп|бр|бпр)$/i },        // ВП — временная нетрудоспособность
  { key: 'admin_leave', re: /^(я[рр]|нс)$/i },  // ЯР/Я-Р — с разрешения администрации
  { key: 'fact_days', re: /^я(-?р)?$/i },       // Я — явка
  { key: 'vacation', re: /^о(д|у|б)?$/i },      // О, ОД, ОУ, ОБ — все виды отпуска
  { key: 'sick', re: /^б$/i },                  // Б — болезнь
  { key: 'weekend_holiday', re: /^в$/i },       // В — выходные
  { key: 'other_absence', re: /^н$/i },         // Н — неявка по невыясненным причинам
]

// Унификация ключа для сравнения кодов: trim + lowercase + удаление
// пробелов/дефисов («Я-Р» == «ЯР», «8 с» == «8с»).
function canonCode(s) {
  return normalizeCodeKey(s).replace(/[\s\-]/g, '')
}

// Unicode-устойчивая замена похожих латинских букв кириллицей (е↔є, i↔і и т.п.)
function foldChars(s) {
  const map = { 'е': 'е', 'є': 'е', 'i': 'и', 'і': 'и', 'ј': 'и' }
  return String(s).split('').map(ch => map[ch] || ch).join('')
}

// Эвристики должны сопоставляться ТОЛЬКО с нормализованным текстом: иначе
// значение из ячейки («отпуск », «Отпуск» с латинской «e») молча не попадало
// ни в одну суммирующую колонку — на печати «Отпуск» выходил нулём.
const NAME_HINTS_NORM = NAME_HINTS.map(h => ({ key: h.key, re: new RegExp(h.re.source, h.re.flags) }))
const STANDARD_CODE_HINTS_NORM = STANDARD_CODE_HINTS.map(h => ({ key: h.key, re: new RegExp(h.re.source.replace(/\^/, ''), h.re.flags) }))

// Ключевые слова «рабочего» кода (явка) — для значений вне справочника.
const WORK_NAME_RE = /^(явк|работ|смен|труд)/i

export function guessDestByText(rawText) {
  const s = foldChars(normalizeCodeKey(rawText))
  if (!s) return null
  for (const h of NAME_HINTS_NORM) {
    if (h.re.test(s)) return h.key
  }
  const codeOnly = s.replace(/[\s\-]/g, '')
  for (const h of STANDARD_CODE_HINTS_NORM) {
    if (h.re.test(codeOnly)) return h.key
  }
  if (WORK_NAME_RE.test(s)) return 'fact_days'
  return null
}

export function guessDestByCode(codeObj) {
  if (!codeObj) return null
  return guessDestByText(String(codeObj.name || '')) || guessDestByText(String(codeObj.code || ''))
}

// Есть ли у кода собственные часы (рабочий код).
function codeHasHours(codeObj) {
  return !!codeObj && ((Number(codeObj.hours_day) || 0) > 0 ||
    (Number(codeObj.hours_night) || 0) > 0 ||
    !!codeObj.use_schedule_hours)
}

// Неявочные колонки: день НЕ является фактической работой.
const ABSENCE_DESTS = ['vacation', 'sick', 'admin_leave', 'other_absence']

// Ключевые слова НЕРАБОЧИХ кодов (неявки/события), которые НЕ являются
// фактической работой и НЕ должны получать автоматические рабочие колонки
// (fact_days/total_hours/tariff_hours), даже если в справочнике проставлены
// часы (например, отпускные или командировочные). Проверяются ПЕРЕД
// WORK_NAME_RE, чтобы «Учебный отпуск» не распознавался как «работ…».
const NONWORK_NAME_RE = /(отпуск|болел|больничн|нетрудоспов|выходн|праздник|праздн|нерабоч|неявк|прогул|отстранен|командиров|медосмотр|декрет|беременн|за свой счет|без сохран)/i

// Стандартные НЕРАБОЧИЕ коды Т-13 (буква кода → тип неявки). Применяется
// только когда название ничего не подсказало. Позволяет отличить «В» (Выходной)
// от произвольного рабочего кода без подсказок.
const NONWORK_CODE_RE = /^(о|од|оу|об|вп|бр|бпр|б|яр|я-р|нс|в|н)$/i

// Эвристика для кодов из справочника БЕЗ явных назначений: определяет, что
// код является НЕЯВКОЙ/СОБЫТИЕМ (не фактической работой). Использует те же
// NAME_HINTS / STANDARD_CODE_HINTS, но с приоритетом неявочных слов над
// общими рабочими ключевыми словами.
function isNonWorkCodeByHeuristic(codeObj) {
  if (!codeObj) return false
  const name = String(codeObj.name || '')
  const code = String(codeObj.code || '')
  if (NONWORK_NAME_RE.test(name)) return true
  if (NONWORK_CODE_RE.test(code.trim().toLowerCase())) return true
  return false
}

// Эффективные destinations кода: явные назначения из справочника имеют
// безусловный приоритет; если они пусты — применяется эвристика по
// названию/коду (см. NAME_HINTS, STANDARD_CODE_HINTS). Для рабочего кода
// без подсказки — стандартная явка. Коды «выходные/праздники» дополнительно
// дают часы в «Итого часов» и «по тарифу» (работа в выходной оплачивается).
export function effectiveDests(codeObj) {
  const explicit = Array.isArray(codeObj && codeObj.destinations) ? codeObj.destinations : []
  if (explicit.length > 0) return explicit
  if (!codeObj) return []
  const guessed = guessDestByCode(codeObj)
  // Неявка (отпуск/болезнь/административный/прочие) — только своя колонка,
  // НИКАКИХ рабочих часов, даже если в справочнике проставлены hours_day.
  if (guessed && ABSENCE_DESTS.includes(guessed)) return [guessed]
  if (guessed === 'weekend_holiday') {
    // Выходной/праздник: дни отдыха; часы добавляются только если у кода
    // заданы собственные часы (например, работа в выходной).
    if (codeHasHours(codeObj)) return ['weekend_holiday', 'total_hours', 'tariff_hours']
    return ['weekend_holiday']
  }
  if (guessed) return [guessed]
  // Если код распознан как НЕРАБОЧИЙ (неявка/событие) — не добавляем
  // автоматические рабочие колонки; пользователь должен явно указать
  // destinations, если хочет распределить часы по колонкам.
  if (isNonWorkCodeByHeuristic(codeObj)) return []
  // Рабочий код с часами (или use_schedule_hours) — стандартная явка.
  if (codeHasHours(codeObj)) return ['fact_days', 'total_hours', 'tariff_hours']
  return []
}

// Итоговые колонки — ТОЧНО КАК В TABELFILL.VUE
// Колонка «Итого часов» перемещена в конец — она крайняя справа и шире
// остальных (45px против 30px). Ширины задаются ЧЕРЕЗ CSS-классы
// (.col-summary-header / .col-summary-cell / .col-total-hours), а не здесь.
// Сверхурочные разделены на две независимые колонки:
// overtime_total  — «итого» (сверхурочные часы + сверхурочные дни × норма дня);
// overtime_hours  — только сверхурочные часы без учёта дней.
export const summaryColumns = [
  { key: 'fact_days', label: 'фактической работы', unit: 'days' },
  { key: 'vacation', label: 'трудовой отпуск', unit: 'days' },
  { key: 'sick', label: 'болезнь', unit: 'days' },
  { key: 'admin_leave', label: 'с разрешения администрации', unit: 'days' },
  { key: 'weekend_holiday', label: 'выходные и праздн.', unit: 'days' },
  { key: 'other_absence', label: 'Другие неявки', unit: 'days' },
  { key: 'overtime_days', label: 'сверхурочные дни', unit: 'days' },
  { key: 'overtime_total', label: 'Сверхурочные часы итого', unit: 'hours' },
  { key: 'overtime_hours', label: 'Сверхурочные часы без дней', unit: 'hours' },
  { key: 'night_hours', label: 'ночные часы', unit: 'hours' },
  { key: 'kdu_work_days', label: 'КДУ', unit: 'manual' },
  { key: 'kdu_weekend_days', label: 'КДУ вых. дня', unit: 'manual' },
  { key: 'tariff_hours', label: 'Часы по тарифу', unit: 'hours' },
  // «Итого часов» — крайняя справа, ширина в 1.5 раза больше остальных (CSS)
  { key: 'total_hours', label: 'Итого часов', unit: 'hours' }
]

// Форматирование ФИО: "Борков Антон Петрович" → "Борков А.П."
export function formatShortName(fullName) {
  if (!fullName) return ''
  const parts = String(fullName).trim().split(/\s+/)

  if (parts.length >= 3) {
    // Фамилия Имя Отчество → Фамилия И.О.
    return `${parts[0]} ${parts[1][0].toUpperCase()}.${parts[2][0].toUpperCase()}.`
  } else if (parts.length === 2) {
    // Фамилия Имя → Фамилия И.
    return `${parts[0]} ${parts[1][0].toUpperCase()}.`
  } else {
    // Только фамилия
    return parts[0]
  }
}

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
  const codes = Array.isArray(timeCodes) ? timeCodes : []
  const codeObj = codes.find(c => String(c.code || '').toLowerCase() === s.toLowerCase())
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
  const codes = Array.isArray(timeCodes) ? timeCodes : []
  const c = codes.find(x => String(x.code || '').toLowerCase() === s)
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
// Ключ поиска в справочнике: trim + lowercase (единый нормализатор для
// кодов справочника и значений ячеек — иначе «я » / « Я» не совпадали).
export function normalizeCodeKey(v) {
  return String(v ?? '').trim().toLowerCase()
}

// Предупреждение о значениях, которых нет в справочнике «Коды часов»:
// раньше они молча исчезали из итогов (пустые колонки на печати).
// Логируем один раз на значение, чтобы не спамить при каждом пересчёте.
const warnedUnknownCodes = new Set()
export function warnUnknownCode(val) {
  const s = String(val ?? '').trim()
  if (!s) return
  if (rawToHours(s) !== null) return // числовой ввод — не ошибка
  if (warnedUnknownCodes.has(s)) return
  warnedUnknownCodes.add(s)
  console.warn(`Значение «${s}» не найдено в справочнике «Коды часов» — в итоги оно не войдёт.`)
}

// Значение ячейки за день d. FastAPI сериализует dict[int, str] с КЛЮЧАМИ-
// СТРОКАМИ («{"1": "Я", "2": "В"}»), поэтому обращение по ЧИСЛУ row.days[1]
// в JS работает только благодаря автоконвертации ключей объекта… НО если days
// пришёл/собран иначе (Map, вложенный объект), доступ мог промахнуться и
// расчёт получил бы пустоту. Читаем оба варианта.
function dayValue(rowDays, d) {
  if (!rowDays) return ''
  if (typeof rowDays.get === 'function' && !(d in rowDays)) {
    const v = rowDays.get(d) ?? rowDays.get(String(d))
    return v == null ? '' : String(v)
  }
  const v = rowDays[d] ?? rowDays[String(d)]
  return v == null ? '' : String(v)
}

export function calculateSummary(row, tabel, timeCodes) {
  const summary = {}
  summaryColumns.forEach(col => { if (col.unit !== 'manual') summary[col.key] = 0 })

  // Defensive: без справочника кодов расчёт всё равно должен показывать
  // числовые значения ячеек, а не «пустоту».
  const codes = Array.isArray(timeCodes) ? timeCodes : []
  const daysInMonth = Number(tabel && tabel.days_in_month) || 31
  const rowDays = (row && row.days) || {}

  // Индекс справочника по нормализованному коду. Раньше поиск шёл через
  // strict-equality lowercase-строк: любое отличие в регистре/пробелах
  // (лидер/трейл пробелы, разная раскладка «e»/«е») — и код НЕ распознавался,
  // все ячейки считались нераспознанными → ИТОГОВЫЕ КОЛОНКИ НА ПЕЧАТИ ВЫХОДИЛИ
  // ПУСТЫМИ. Нормализуем обе стороны: trim + lowercase.
  const codeIndex = new Map()
  // Канон-индекс: код без пробелов/дефисов («Я-Р» найдёт «ЯР» из ячейки).
  // Заполняется только при отсутствии коллизий — явное точное совпадение
  // всегда имеет приоритет.
  const canonIndex = new Map()
  for (const c of codes) {
    const key = normalizeCodeKey(c && c.code)
    if (key && !codeIndex.has(key)) codeIndex.set(key, c)
    const ck = canonCode(c && c.code)
    if (ck && !canonIndex.has(ck)) canonIndex.set(ck, c)
  }
  const findCode = (val) => {
    const exact = codeIndex.get(normalizeCodeKey(val))
    if (exact) return exact
    return canonIndex.get(canonCode(val)) || null
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const val = dayValue(rowDays, d).trim()
    if (!val) continue

    // Норма по графику работы для этого дня недели (fallback: norm_hours или 8)
    const norm = getDayNorm(row, d)

    const codeObj = findCode(val)

    if (!codeObj) {
      // Числовой ввод («8», «8ч15м»), которого нет в справочнике — ниже.
      if (rawToHours(val) === null) {
        // ИСПРАВЛЕНИЕ БАГА «при печати не считает суммирующие колонки, например
        // "Отпуск"»: значение НЕ найдено в справочнике (значения в табеле могли
        // быть введены текстом/кодом с другим регистром/дефисом/раскладкой).
        // Раньше такие ячейки молча исчезали из итогов. Теперь для неявок
        // применяется эвристика по тексту (NAME_HINTS / STANDARD_CODE_HINTS):
        // «отпуск», «О», «ОД», «больничный» и т.п. попадают в свою колонку.
        const guessed = guessDestByText(val)
        if (guessed) {
          const colDef = summaryColumns.find(c => c.key === guessed)
          if (colDef && colDef.unit === 'days') {
            summary[guessed] += 1
            continue
          }
          if (guessed === 'fact_days') {
            // «явка» текстом без кода: день считаем, часов не знаем
            summary.fact_days += 1
            continue
          }
        }
        // Значение похоже на код, но ни в справочнике, ни эвристикой не
        // распознано — молча обнулять итоги нельзя: предупреждаем.
        warnUnknownCode(val)
        continue
      }
    }

    // Числовой ввод («8», «8ч15м», «8:15»), которого НЕТ в справочнике:
    // обычные часы + сверхурочные сверх нормы по графику.
    // «Сверхурочные дни» при числовом вводе НЕ добавляются.
    // ВАЖНО: если код есть в справочнике (например «7» = Выходной),
    // он обрабатывается ниже как код — а не как 7 часов.
    if (rawToHours(val) !== null) {
      const hours = rawToHours(val)
      if (hours > 0) {
        const regular = Math.min(hours, norm)
        const ot = Math.max(0, hours - norm)
        summary.total_hours += hours
        summary.fact_days += 1
        summary.tariff_hours += regular
        if (ot > 0) {
          summary.overtime_hours += ot
        }
      }
      continue
    }

    // ===== Обработка кода из справочника =====
    // «Время по графику»: часы кода = норма графика на этот день (см. codeHoursForDay)
    const eff = codeHoursForDay(codeObj, row, d)
    const hoursDay = eff.day
    const hoursNight = eff.night
    const totalHoursE = eff.total
    // ЭВРИСТИКА (см. NAME_HINTS / STANDARD_CODE_HINTS / effectiveDests):
    // у кода НЕ заданы назначения → раньше он не попадал НИ В ОДНУ суммирующую
    // колонку («Отпуск» печатался нулём). effectiveDests возвращает явные
    // destinations (приоритет всегда у настроек пользователя); пустые
    // назначения заполняются по названию/букве кода справочника.
    const dests = effectiveDests(codeObj)

    // Явные назначения имеют безусловный приоритет. Если они заданы, используем
    // их как есть; иначе применяем эвристику effectiveDests.
    const explicitDestinations = Array.isArray(codeObj.destinations) ? codeObj.destinations : []
    const useExplicit = explicitDestinations.length > 0
    const effective = useExplicit ? explicitDestinations : dests

    // Флаг неявочного кода: если в эффективных назначениях есть хоть одна
    // неявочная колонка — код считается неявкой (не получает рабочих часов).
    const isAbsenceCode = effective.some(d => ABSENCE_DESTS.includes(d))

    // Назначения, которые нужно обработать: все, кроме total_hours/tariff_hours
    // (они обрабатываются централизованно ниже). Для кодов без явных назначений
    // effectiveDests уже вернул нужную колонку (например vacation/sick).
    const toProcess = effective.filter(d => d !== 'total_hours' && d !== 'tariff_hours')

    toProcess.forEach(dest => {
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

    // Централизованный досчёт рабочих колонок (фактические дни, итого часов,
    // тарифные часы) для НЕ-неявочных кодов с часами. Это гарантирует, что
    // даже если пользователь не задал destinations для рабочего кода, его
    // часы всё равно попадут в итоги. Для неявок часы НЕ добавляются.
    if (!isAbsenceCode && (totalHoursE > 0 || codeHasHours(codeObj))) {
      if (!effective.includes('fact_days')) summary.fact_days += 1
      summary.total_hours += totalHoursE
      summary.tariff_hours += Math.min(totalHoursE, norm > 0 ? norm : totalHoursE)
    }

    // Логика сверхурочных ЧАСОВ и ДНЕЙ разделена:
    // - коды с направлением overtime_hours уже добавили ВСЕ свои часы выше;
    // - «Время по графику» + выходные часы: работа в законный выходной
    //   (норма = 0) — ВСЕ эти часы считаются сверхурочными.
    //   Дни отдыха («В») с нулевыми часами в сверхурочные НЕ попадают.
    // - обычный код: сверхурочные = превышение фактических часов над нормой.
    const isOvertimeCode = effective.includes('overtime_hours') || effective.includes('overtime_days')
    if (codeObj.use_schedule_hours && !isOvertimeCode && !isAbsenceCode && norm <= 0 && totalHoursE > 0) {
      summary.overtime_hours += totalHoursE
    } else if (!isAbsenceCode && totalHoursE > 0 && !isOvertimeCode && !codeObj.use_schedule_hours) {
      const ot = Math.max(0, totalHoursE - norm)
      if (ot > 0) {
        summary.overtime_hours += ot
        // из колонок обычных часов вычитаем превышение — теперь всегда:
        // рабочие часы досчитываются централизованно для всех НЕ-неявочных
        // кодов (см. выше), поэтому «по тарифу» содержит не более нормы,
        // а всё превышение принадлежит сверхурочным.
        summary.tariff_hours = Math.max(0, summary.tariff_hours - ot)
        // «Итого часов» остаётся полным (все введённые часы)
      }
    }
  }

  // ИСПРАВЛЕНИЕ: колонка «выходные и праздн.» раньше считалась ТОЛЬКО если
  // в ячейках стояли коды с таким направлением. В форме Т-13 эта колонка —
  // количество дней отдыха по графику, поэтому добавляем дни из
  // tabel.weekend_days / tabel.holiday_days, которые НЕ отмечены кодом с
  // явным назначением (пустые ячейки и числовой ввод не создают неявок).
  const weekendHolidaySet = new Set()
  for (const list of [tabel && tabel.weekend_days, tabel && tabel.holiday_days]) {
    if (Array.isArray(list)) list.forEach(x => { const n = Number(x); if (n > 0) weekendHolidaySet.add(n) })
  }
  for (const d of weekendHolidaySet) {
    const val = dayValue(rowDays, d).trim()
    if (!val) continue
    const codeObj = findCode(val)
    // Если у кода назначения заданы явно — пользователь контролирует колонку
    // сам; эвристика/автоподсчёт не вмешивается.
    if (codeObj && Array.isArray(codeObj.destinations) && codeObj.destinations.length > 0) continue
    summary.weekend_holiday += 1
  }

  // Сверхурочные ДНИ тоже считаются сверхурочной работой:
  // 1 день = норма часов этого дня (из графика; fallback norm_hours/8).
  // Итого = сверхурочные часы + Σ(дни × норма); overtime_hours — «часы без дней».
  let otDaysHours = 0
  for (let d = 1; d <= daysInMonth; d++) {
    const codeObj = findCode(dayValue(rowDays, d))
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
  const codes = Array.isArray(timeCodes) ? timeCodes : []
  const codeObj = codes.find(c => String(c.code || '').toLowerCase() === s.toLowerCase())
  if (codeObj) {
    const eff = codeHoursForDay(codeObj, row, d)
    // Если есть часы — возвращаем число («8.25»), иначе — сам код («К», «В», «О»)
    return eff.total > 0 ? fmtNum(eff.total) : s
  }
  // Числовое значение
  return s
}
