"""
Calendário de dias úteis para mercados financeiros.
Suporta B3, NYSE, e detecção genérica.
"""

from datetime import date, timedelta
from typing import List

# Feriados fixos B3 (mês, dia) — exclui móveis como Carnaval e Corpus Christi
B3_FIXED_HOLIDAYS = [
    (1, 1),   # Ano Novo
    (4, 21),  # Tiradentes
    (5, 1),   # Dia do Trabalho
    (9, 7),   # Independência
    (10, 12), # Nossa Senhora Aparecida
    (11, 2),  # Finados
    (11, 15), # Proclamação da República
    (12, 25), # Natal
]

# Feriados fixos NYSE
NYSE_FIXED_HOLIDAYS = [
    (1, 1),   # New Year's Day
    (7, 4),   # Independence Day
    (12, 25), # Christmas Day
]


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def is_b3_holiday(d: date) -> bool:
    return (d.month, d.day) in B3_FIXED_HOLIDAYS


def is_nyse_holiday(d: date) -> bool:
    return (d.month, d.day) in NYSE_FIXED_HOLIDAYS


def is_business_day(d: date, market: str = "generic") -> bool:
    """Verifica se uma data é dia útil para o mercado especificado."""
    if is_weekend(d):
        return False
    if market.upper() == "B3":
        return not is_b3_holiday(d)
    if market.upper() in ("NYSE", "NASDAQ", "US"):
        return not is_nyse_holiday(d)
    return True  # genérico: só pula fim de semana


def business_days_range(start: date, end: date, market: str = "generic") -> List[date]:
    """Retorna lista de dias úteis entre start e end (inclusive)."""
    days = []
    current = start
    while current <= end:
        if is_business_day(current, market):
            days.append(current)
        current += timedelta(days=1)
    return days


def last_n_business_days(n: int, from_date: date | None = None, market: str = "generic") -> List[date]:
    """Retorna os últimos N dias úteis a partir de from_date."""
    if from_date is None:
        from_date = date.today()
    days = []
    current = from_date
    while len(days) < n:
        if is_business_day(current, market):
            days.append(current)
        current -= timedelta(days=1)
    days.reverse()
    return days
