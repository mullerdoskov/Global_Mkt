"""
data/calendar.py
Calendário de dias úteis BR/US/UK/DE/FR usando a biblioteca holidays.
"""

from datetime import date, timedelta
import holidays


# Mapeamento exchange → país holidays
EXCHANGE_COUNTRY_MAP = {
    "B3": "BR",
    "NYSE": "US",
    "NASDAQ": "US",
    "LSE": "GB",
    "XETRA": "DE",
    "EURONEXT_PA": "FR",
}


def generate_trading_calendar(year: int, exchanges: list[str] = None) -> list[dict]:
    """
    Gera o calendário de dias úteis para o ano especificado.
    Retorna lista de dicts prontos para inserção no banco.
    """
    if exchanges is None:
        exchanges = list(EXCHANGE_COUNTRY_MAP.keys())

    calendar_entries = []

    for exchange in exchanges:
        country_code = EXCHANGE_COUNTRY_MAP.get(exchange)
        if not country_code:
            continue

        # Obter feriados do país
        country_holidays = holidays.country_holidays(country_code, years=year)

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        current = start_date

        while current <= end_date:
            # Dia útil = não é fim de semana E não é feriado
            is_weekend = current.weekday() >= 5
            holiday_name = country_holidays.get(current)
            is_business_day = not is_weekend and holiday_name is None

            calendar_entries.append({
                "date": current,
                "exchange": exchange,
                "is_business_day": is_business_day,
                "holiday_name": holiday_name if holiday_name else None,
            })

            current += timedelta(days=1)

    return calendar_entries


def get_business_days(exchange: str, start: date, end: date) -> list[date]:
    """Retorna lista de dias úteis entre duas datas para uma bolsa."""
    country_code = EXCHANGE_COUNTRY_MAP.get(exchange, "US")
    country_holidays = holidays.country_holidays(country_code, years=range(start.year, end.year + 1))

    business_days = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in country_holidays:
            business_days.append(current)
        current += timedelta(days=1)

    return business_days


if __name__ == "__main__":
    from datetime import date
    cal = generate_trading_calendar(2026)
    bdays = [e for e in cal if e["is_business_day"]]
    print(f"Total de entradas: {len(cal)}")
    print(f"Dias úteis: {len(bdays)}")
    print(f"Feriados: {len([e for e in cal if e['holiday_name']])}")
