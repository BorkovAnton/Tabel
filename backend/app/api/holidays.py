"""Производственный календарь: загрузка с xmlcalendar.ru и выдача выходных/праздников.

Источник данных: https://xmlcalendar.ru/index.php?country=by (Беларусь).
Формат XML: https://xmlcalendar.ru/data/{country}/{year}/calendar.xml
  <day d="01.01" t="1" h="1"/>  — t=1 нерабочий день, t=2 рабочий день после праздника;
                                    h=id праздника из блока <holidays>.
Данные сохраняются в таблицу holiday_calendars; weekends считаются по пятидневке
(суббота/воскресенье), праздники — из XML.
"""
import calendar
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.holiday_calendar import HolidayCalendar
from app.models.user import User

router = APIRouter(prefix="/holidays", tags=["Holidays"])

SOURCE_URL_TEMPLATE = "https://xmlcalendar.ru/data/{country}/{year}/calendar.xml"
HTTP_TIMEOUT = 20


def _parse_calendar_xml(xml_bytes: bytes, year: int) -> list[dict]:
    """Возвращает список {date, is_holiday, is_weekend, description} для всех дней года."""
    root = ET.fromstring(xml_bytes)

    holiday_titles: dict[str, str] = {}
    holidays_node = root.find("holidays")
    if holidays_node is not None:
        for h in holidays_node.findall("holiday"):
            holiday_titles[h.get("id")] = h.get("title") or ""

    # Сначала отмечаем все дни как рабочие, выходные — по пятидневке
    days: dict[date, dict] = {}
    for m in range(1, 13):
        for d in range(1, calendar.monthrange(year, m)[1] + 1):
            dt = date(year, m, d)
            days[dt] = {
                "date": dt,
                "is_holiday": False,
                "is_weekend": dt.weekday() in (5, 6),  # сб, вс
                "description": None,
            }

    overrides: dict[date, tuple[int, str | None]] = {}
    days_node = root.find("days")
    if days_node is not None:
        for day in days_node.findall("day"):
            d_attr = day.get("d")  # формат ММ.ДД
            t_attr = day.get("t")
            if not d_attr or not t_attr:
                continue
            try:
                mm, dd = d_attr.split(".")
                dt = date(year, int(mm), int(dd))
            except ValueError:
                continue
            title = holiday_titles.get(day.get("h"))
            overrides[dt] = (int(t_attr), title)

    for dt, (t, title) in overrides.items():
        if dt not in days:
            continue
        if t == 1:  # нерабочий день
            days[dt]["is_holiday"] = True
            days[dt]["is_weekend"] = False  # праздник учитываем отдельно от переносов
            if title:
                days[dt]["description"] = title[:255]
        elif t == 2:  # рабочий день (перенос: раньше был выходным)
            days[dt]["is_weekend"] = False

    return list(days.values())


def _upsert_year(db: Session, parsed: list[dict], country: str) -> int:
    written = 0
    existing = {h.date: h for h in db.query(HolidayCalendar).filter(
        HolidayCalendar.country == country).all()}
    for item in parsed:
        h = existing.get(item["date"])
        if h is None:
            db.add(HolidayCalendar(
                date=item["date"],
                is_holiday=item["is_holiday"],
                is_weekend=item["is_weekend"],
                description=item["description"],
                country=country,
            ))
        else:
            h.is_holiday = item["is_holiday"]
            h.is_weekend = item["is_weekend"]
            h.description = item["description"]
            h.country = country
        written += 1
    db.commit()
    return written


@router.post("/load")
def load_calendar(
    year: int = Query(..., ge=1970, le=2100),
    country: str = Query("by", pattern="^(by|ru)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Загрузить производственный календарь за год с xmlcalendar.ru (только Администратор)."""
    url = SOURCE_URL_TEMPLATE.format(country=country, year=year)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TabelSystem/1.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Не удалось получить календарь с xmlcalendar.ru: {e}")

    try:
        parsed = _parse_calendar_xml(xml_bytes, year)
    except ET.ParseError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка разбора XML-календаря: {e}")

    saved = _upsert_year(db, parsed, country)
    nonworking = sum(1 for p in parsed if p["is_holiday"] or p["is_weekend"])
    holidays = sum(1 for p in parsed if p["is_holiday"])
    return {
        "year": year,
        "country": country,
        "source": url,
        "days_saved": saved,
        "holidays": holidays,
        "nonworking_days_total": nonworking,
    }


@router.get("/{year}")
def get_year(
    year: int,
    country: str = Query("BY", pattern="^(BY|by|RU|ru)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Календарь за год: списки дат выходных и праздников (для подсветки в табеле)."""
    country_u = country.upper()
    rows = db.query(HolidayCalendar).filter(
        HolidayCalendar.country == country_u,
        HolidayCalendar.date >= date(year, 1, 1),
        HolidayCalendar.date <= date(year, 12, 31),
    ).all()
    weekends = sorted(h.date.isoformat() for h in rows if h.is_weekend and not h.is_holiday)
    holidays = sorted(
        [{"date": h.date.isoformat(), "name": h.description or "Праздничный день"} for h in rows if h.is_holiday],
        key=lambda x: x["date"],
    )
    loaded = bool(rows)
    return {"year": year, "country": country_u, "loaded": loaded, "weekends": weekends, "holidays": holidays}
