# FILE: backend/app/services/kosovo_holidays.py
# PHOENIX PROTOCOL - KOSOVO HOLIDAY ENGINE V2.0 (BACKEND PARITY WITH FRONTEND)
# 100% COMPLETE CODE • ZERO PY WARNINGS • PRODUCTION-READY
#
# Ky modul është port i saktë i `frontend/src/utils/kosovoHolidays.ts`.
# Synon të mbajë PARITET të plotë me frontend-in për festat kombëtare,
# zëvendësimin e fundjavës (Sat/Sun → Mon), Pashkët, dhe Bajramet.
#
# Përdoret nga `calendar_service.py` për të llogaritur saktë:
#   - Ditët e punës midis dy datave (working_days)
#   - A është një ditë e caktuar festë zyrtare

from datetime import date, timedelta
from typing import List, Optional, TypedDict


class HolidayDict(TypedDict):
    name: str
    type: str          # 'LEGAL' | 'RELIGIOUS' | 'INTERNATIONAL'
    date: date
    greeting_key: str
    is_moveable: bool


# ==========================================================
# FESTAT FIKSE (me zëvendësim fundjave sipas ligjit të Kosovës)
# ==========================================================
_FIXED_DEFINITIONS = [
    {"name": "Viti i Ri",                    "type": "LEGAL",         "key": "new_year",            "month": 1,  "day": 1},
    {"name": "Krishtlindjet Ortodokse",      "type": "RELIGIOUS",     "key": "orthodox_christmas",  "month": 1,  "day": 7},
    {"name": "Dita e Pavarësisë",            "type": "LEGAL",         "key": "independence_day",    "month": 2,  "day": 17},
    {"name": "Dita e Kushtetutës",           "type": "LEGAL",         "key": "constitution_day",    "month": 4,  "day": 9},
    {"name": "Dita e Punëtorëve",            "type": "INTERNATIONAL", "key": "labor_day",           "month": 5,  "day": 1},
    {"name": "Dita e Evropës",               "type": "INTERNATIONAL", "key": "europe_day",          "month": 5,  "day": 9},
    {"name": "Krishtlindjet Katolike",       "type": "RELIGIOUS",     "key": "catholic_christmas",  "month": 12, "day": 25},
]


def _calculate_catholic_easter(year: int) -> date:
    """Algoritmi Meeus/Jones/Butcher për Pashkët Katolike (Gregorian)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _calculate_orthodox_easter(year: int) -> date:
    """Pashkët Ortodokse (Julian) + 13 ditë = Gregorian (i saktë deri 2099)."""
    a = year % 19
    b = year % 4
    c = year % 7
    d = (19 * a + 15) % 30
    e = (2 * b + 4 * c + 6 * d + 6) % 7
    f = d + e
    day = f + 22
    month = 3
    if day > 31:
        day -= 31
        month = 4
    julian_date = date(year, month, day)
    return julian_date + timedelta(days=13)


# ==========================================================
# FESTAT ISLAME (Bajramet) — Data të përafërta
# ----------------------------------------------------------
# Shënim: Kalendari islamik është hënor. Datat zyrtare në Kosovë
# përcaktohen nga Bashkësia Islame e Kosovës (BIK) çdo vit.
# Të dhënat e mëposhtme janë përllogaritje standarde dhe duhet
# të verifikohen para përdorimit zyrtar në afate ligjore.
# ==========================================================
_EID_DATES = {
    2024: {"fitr": (4, 10), "adha": (6, 16)},
    2025: {"fitr": (3, 31), "adha": (6, 6)},
    2026: {"fitr": (3, 20), "adha": (5, 27)},
    2027: {"fitr": (3, 9),  "adha": (5, 16)},
    2028: {"fitr": (2, 26), "adha": (5, 5)},
    2029: {"fitr": (2, 14), "adha": (4, 24)},
    2030: {"fitr": (2, 4),  "adha": (4, 13)},
}


def _apply_substitution_rule(d: date) -> date:
    """
    Rregulli i Kosovës: nëse festa bie të shtunë → zhvendoset të hënën;
    nëse bie të dielë → zhvendoset të hënën (e njëjta ditë pushimi).
    """
    weekday = d.weekday()  # Monday=0 ... Sunday=6
    if weekday == 6:  # Sunday → Monday
        return d + timedelta(days=1)
    if weekday == 5:  # Saturday → Monday
        return d + timedelta(days=2)
    return d


# ==========================================================
# API PUBLIKE
# ==========================================================
def get_holidays_for_year(year: int) -> List[HolidayDict]:
    """Kthen listën e plotë të festave zyrtare të Kosovës për një vit të caktuar."""
    holidays: List[HolidayDict] = []

    # 1. Festat fikse (me zëvendësim fundjave)
    for defn in _FIXED_DEFINITIONS:
        holidays.append({
            "name": defn["name"],
            "type": defn["type"],
            "date": _apply_substitution_rule(date(year, defn["month"], defn["day"])),
            "greeting_key": defn["key"],
            "is_moveable": False,
        })

    # 2. Pashkët Katolike (lëvizëse)
    holidays.append({
        "name": "Pashkët Katolike",
        "type": "RELIGIOUS",
        "date": _calculate_catholic_easter(year),
        "greeting_key": "catholic_easter",
        "is_moveable": True,
    })

    # 3. Pashkët Ortodokse (lëvizëse)
    holidays.append({
        "name": "Pashkët Ortodokse",
        "type": "RELIGIOUS",
        "date": _calculate_orthodox_easter(year),
        "greeting_key": "orthodox_easter",
        "is_moveable": True,
    })

    # 4. Bajramet (nëse viti është në listën tonë)
    eids = _EID_DATES.get(year)
    if eids:
        holidays.append({
            "name": "Fitër Bajrami",
            "type": "RELIGIOUS",
            "date": _apply_substitution_rule(date(year, eids["fitr"][0], eids["fitr"][1])),
            "greeting_key": "fiter_bajram",
            "is_moveable": True,
        })
        holidays.append({
            "name": "Kurban Bajrami",
            "type": "RELIGIOUS",
            "date": _apply_substitution_rule(date(year, eids["adha"][0], eids["adha"][1])),
            "greeting_key": "kurban_bajram",
            "is_moveable": True,
        })

    return holidays


def get_holiday_for_date(d: date) -> Optional[HolidayDict]:
    """Kthen festën për një datë të caktuar, ose None nëse nuk është festë."""
    for h in get_holidays_for_year(d.year):
        if h["date"] == d:
            return h
    return None


def is_holiday(d: date) -> bool:
    """Kontroll i shpejtë: a është data e dhënë festë zyrtare?"""
    return get_holiday_for_date(d) is not None