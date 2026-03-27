"""
CLI Versátil — Market Platform Unified v2.0

Uso:
    python -m backend.cli <comando> [opções]

Comandos disponíveis:
  ─── BANCO ───
    db-init              Cria tabelas e popula assets
    db-status            Mostra contagens e saúde do banco
    db-reset             Apaga e recria todas as tabelas (DESTRUTIVO)

  ─── INGESTÃO ───
    ingest-prices        Ingere preços (com filtros de data, tipo, país)
    ingest-fundamentals  Ingere demonstrativos financeiros e valuations
    ingest-all           Ingere preços + fundamentals

  ─── CONSULTA (READ) ───
    list-assets          Lista assets com filtros
    search               Busca assets por texto
    show                 Mostra detalhe de um símbolo
    prices               Mostra preços recentes de um símbolo
    top-movers           Maiores altas/baixas do dia

  ─── GERENCIAMENTO ───
    add-asset            Adiciona um asset manualmente
    remove-asset         Desativa um asset
    delete-prices        Remove preços de um símbolo/período
    export               Exporta dados para CSV

Exemplos:
    python -m backend.cli db-init
    python -m backend.cli ingest-prices --type stock --country BR --start 2025-01-01 --end 2025-12-31
    python -m backend.cli ingest-prices --type index --period 6mo
    python -m backend.cli list-assets --type etf --country US
    python -m backend.cli show PETR4.SA
    python -m backend.cli prices AAPL --period 30d
    python -m backend.cli top-movers --country BR --limit 10
    python -m backend.cli add-asset TICKER "Nome" stock BR
    python -m backend.cli export prices --type stock --country BR -o precos_br.csv
"""

import argparse
import csv
import sys
from datetime import date, datetime

from sqlalchemy import func, select, text

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


# ══════════════════════════════════════════════════════════
#  HELPERS DE FORMATAÇÃO
# ══════════════════════════════════════════════════════════

def _c(text_str: str, color: str = "") -> str:
    """Aplica cor se disponível."""
    if not HAS_COLOR or not color:
        return text_str
    colors = {
        "green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW,
        "cyan": Fore.CYAN, "magenta": Fore.MAGENTA, "blue": Fore.BLUE,
        "white": Fore.WHITE, "dim": Style.DIM,
    }
    c = colors.get(color, "")
    return f"{c}{text_str}{Style.RESET_ALL}"


def _header(title: str):
    print(f"\n{_c('═' * 60, 'cyan')}")
    print(f"  {_c(title, 'cyan')}")
    print(f"{_c('═' * 60, 'cyan')}\n")


def _ok(msg: str):
    print(f"  {_c('✓', 'green')} {msg}")


def _err(msg: str):
    print(f"  {_c('✗', 'red')} {msg}")


def _info(msg: str):
    print(f"  {_c('→', 'yellow')} {msg}")


def _table(headers: list, rows: list, widths: list | None = None):
    """Imprime tabela formatada no terminal."""
    if not rows:
        print("  (sem dados)")
        return

    if widths is None:
        widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
        widths = [min(w, 40) for w in widths]  # cap

    # Header
    header_line = "  " + " │ ".join(str(h).ljust(w)[:w] for h, w in zip(headers, widths))
    separator = "  " + "─┼─".join("─" * w for w in widths)
    print(_c(header_line, "white"))
    print(_c(separator, "dim"))

    # Rows
    for row in rows:
        cells = []
        for i, (val, w) in enumerate(zip(row, widths)):
            s = str(val) if val is not None else "—"
            # Colorir change_pct
            if isinstance(val, (int, float)) and "change" in headers[i].lower():
                if val > 0:
                    s = _c(f"+{val:.2f}%", "green")
                elif val < 0:
                    s = _c(f"{val:.2f}%", "red")
                else:
                    s = f"{val:.2f}%"
                cells.append(s.ljust(w + 20))  # compensar ANSI codes
            else:
                cells.append(s.ljust(w)[:w])
        print("  " + " │ ".join(cells))


# ══════════════════════════════════════════════════════════
#  COMANDOS: BANCO
# ══════════════════════════════════════════════════════════

def cmd_db_init(args):
    """Cria tabelas e popula assets do symbols.py."""
    from backend.db.connection import init_db, drop_db, get_session, engine
    from backend.db.schema import Asset, AssetType, Base
    from backend.config.symbols import ALL_SYMBOLS
    from backend.data.sectors_gics import COUNTRIES
    from backend.db.schema import Country, SectorGICS
    from backend.data.sectors_gics import GICS_INDUSTRY_GROUPS, get_sector_name

    _header("Inicializando Banco de Dados")

    # Verificar se schema antigo existe e é incompatível
    needs_rebuild = False
    try:
        with engine.connect() as conn:
            # Testar se a tabela countries tem a coluna 'code' (schema novo)
            conn.execute(text("SELECT code FROM countries LIMIT 1"))
    except Exception as e:
        err_str = str(e).lower()
        if "não existe" in err_str or "does not exist" in err_str or "no such column" in err_str:
            needs_rebuild = True
            _info("Schema antigo detectado (incompatível com v2.0)")
        # Se a tabela não existe, tudo bem — será criada
        elif "relation" in err_str and "does not exist" in err_str:
            pass  # primeira execução

    if needs_rebuild:
        _info("Recriando tabelas com schema novo...")
        if not getattr(args, 'force', False):
            resp = input(f"  {_c('ATENÇÃO:', 'red')} Tabelas antigas serão recriadas (dados antigos perdidos). Continuar? [s/N]: ")
            if resp.lower() not in ("s", "sim", "y", "yes"):
                _info("Cancelado. Use 'db-reset --force' + 'db-init' se preferir fazer manualmente.")
                return
        drop_db()
        _ok("Tabelas antigas removidas")

    # Criar tabelas (CREATE IF NOT EXISTS)
    init_db()
    _ok("Tabelas criadas/verificadas (9 tabelas)")

    with get_session() as session:
        # Popular países
        try:
            existing_countries = {r[0] for r in session.execute(select(Country.code)).fetchall()}
        except Exception:
            existing_countries = set()

        new_countries = 0
        for code, info in COUNTRIES.items():
            if code not in existing_countries:
                session.add(Country(code=code, name=info["name"], currency=info["currency"], exchange=info["exchange"]))
                new_countries += 1
        if new_countries:
            session.flush()
            _ok(f"{new_countries} países inseridos")
        else:
            _info("Países já existem")

        # Popular setores GICS
        try:
            existing_sectors = {r[0] for r in session.execute(select(SectorGICS.gics_code)).fetchall()}
        except Exception:
            existing_sectors = set()

        new_sectors = 0
        for code, name in GICS_INDUSTRY_GROUPS.items():
            if code not in existing_sectors:
                session.add(SectorGICS(gics_code=code, sector_name=get_sector_name(code), industry_group=name))
                new_sectors += 1
        if new_sectors:
            session.flush()
            _ok(f"{new_sectors} setores GICS inseridos")
        else:
            _info("Setores já existem")

        # Popular assets
        try:
            existing_assets = {r[0] for r in session.execute(select(Asset.symbol)).fetchall()}
        except Exception:
            existing_assets = set()

        new_assets = 0
        for sym, name, atype, country in ALL_SYMBOLS:
            if sym not in existing_assets:
                session.add(Asset(symbol=sym, name=name, asset_type=AssetType(atype), country=country))
                new_assets += 1
        if new_assets:
            _ok(f"{new_assets} assets inseridos")
        else:
            _info("Assets já existem")

        session.commit()

    # Status final
    cmd_db_status(args)


def cmd_db_status(args):
    """Mostra contagens e status do banco."""
    from backend.db.connection import check_connection, engine

    _header("Status do Banco de Dados")

    status = check_connection()
    if status["status"] == "ok":
        _ok(f"Conexão: {status['url']}")
    else:
        _err(f"Conexão falhou: {status.get('error')}")
        return

    try:
        with engine.connect() as conn:
            tables = [
                "countries", "sectors_gics", "companies", "assets",
                "trading_calendar", "prices_daily", "financial_statements",
                "valuation_multiples", "ingestion_log",
            ]
            print()
            for t in tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                    status_icon = _c("●", "green") if count > 0 else _c("○", "dim")
                    print(f"  {status_icon} {t:<30} {_c(str(count), 'yellow')} registros")
                except Exception:
                    print(f"  {_c('○', 'dim')} {t:<30} (tabela não existe)")

            # Assets por tipo
            print(f"\n  {_c('Assets por tipo:', 'white')}")
            rows = conn.execute(text(
                "SELECT asset_type, COUNT(*) FROM assets GROUP BY asset_type ORDER BY COUNT(*) DESC"
            )).fetchall()
            for atype, count in rows:
                print(f"    {atype:<15} {count}")

            # Assets por país (top 5)
            print(f"\n  {_c('Top 5 países:', 'white')}")
            rows = conn.execute(text(
                "SELECT country, COUNT(*) FROM assets WHERE country IS NOT NULL "
                "GROUP BY country ORDER BY COUNT(*) DESC LIMIT 5"
            )).fetchall()
            for country, count in rows:
                print(f"    {country:<10} {count}")

    except Exception as e:
        _err(f"Erro ao consultar: {e}")


def cmd_db_reset(args):
    """Reset destrutivo do banco."""
    from backend.db.connection import drop_db, init_db

    _header("RESET DO BANCO (DESTRUTIVO)")

    if not args.force:
        resp = input(f"  {_c('ATENÇÃO:', 'red')} Isso vai APAGAR todos os dados. Confirma? [s/N]: ")
        if resp.lower() not in ("s", "sim", "y", "yes"):
            _info("Cancelado")
            return

    drop_db()
    _ok("Tabelas removidas")
    init_db()
    _ok("Tabelas recriadas (vazias)")
    _info("Execute 'db-init' para popular os assets novamente")


# ══════════════════════════════════════════════════════════
#  COMANDOS: INGESTÃO
# ══════════════════════════════════════════════════════════

def cmd_ingest_prices(args):
    """Ingere preços com filtros."""
    from backend.ingestion.loader import ingest_prices

    _header("Ingestão de Preços")

    filters = []
    if args.type:
        filters.append(f"tipo={args.type}")
    if args.country:
        filters.append(f"país={args.country}")
    if args.start:
        filters.append(f"início={args.start}")
    if args.end:
        filters.append(f"fim={args.end}")
    if not args.start:
        filters.append(f"período={args.period}")

    _info(f"Filtros: {', '.join(filters) if filters else 'nenhum (todos)'}")

    symbols_filter = None
    if args.symbols:
        from backend.config.symbols import ALL_SYMBOLS
        sym_list = [s.strip() for s in args.symbols.split(",")]
        symbols_filter = [s for s in ALL_SYMBOLS if s[0] in sym_list]
        _info(f"Símbolos específicos: {len(symbols_filter)}")

    result = ingest_prices(
        symbols=symbols_filter,
        start=args.start,
        end=args.end,
        period=args.period,
        asset_type=args.type,
        country=args.country,
    )

    print()
    _ok(f"Concluído: {result['success']}/{result['total_symbols']} OK")
    _info(f"Inseridos: {result['rows_inserted']} | Atualizados: {result['rows_updated']}")
    if result["errors"] > 0:
        _err(f"Erros: {result['errors']}")
        for err in result["error_details"][:5]:
            print(f"    {_c(err['symbol'], 'yellow')}: {err['error'][:80]}")


def cmd_ingest_fundamentals(args):
    """Ingere fundamentos."""
    from backend.ingestion.fundamentals_loader import ingest_fundamentals

    _header("Ingestão de Fundamentos")

    symbols_filter = None
    if args.symbols:
        symbols_filter = [s.strip() for s in args.symbols.split(",")]

    result = ingest_fundamentals(
        asset_type=args.type or "stock",
        country=args.country,
        symbols_filter=symbols_filter,
    )

    _ok(f"Concluído: {result['success']}/{result['total']} OK")
    if result["errors"] > 0:
        _err(f"Erros: {result['errors']}")


def cmd_ingest_all(args):
    """Ingere preços e fundamentos."""
    _header("Ingestão Completa")
    _info("Fase 1/2: Preços")
    cmd_ingest_prices(args)
    print()
    _info("Fase 2/2: Fundamentos")
    cmd_ingest_fundamentals(args)


# ══════════════════════════════════════════════════════════
#  COMANDOS: CONSULTA (READ)
# ══════════════════════════════════════════════════════════

def cmd_list_assets(args):
    """Lista assets com filtros."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset

    _header("Assets")

    with get_session() as session:
        query = select(Asset).where(Asset.is_active == True)
        if args.type:
            query = query.where(Asset.asset_type == args.type)
        if args.country:
            query = query.where(Asset.country == args.country.upper())
        query = query.order_by(Asset.symbol).limit(args.limit)

        assets = session.execute(query).scalars().all()

        headers = ["Símbolo", "Nome", "Tipo", "País"]
        rows = [
            (a.symbol, a.name[:35], a.asset_type.value if hasattr(a.asset_type, "value") else a.asset_type, a.country)
            for a in assets
        ]
        _table(headers, rows, [15, 35, 12, 8])
        print(f"\n  Total: {len(rows)} assets")


def cmd_search(args):
    """Busca assets por texto."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset

    _header(f"Busca: '{args.query}'")

    with get_session() as session:
        pattern = f"%{args.query}%"
        assets = session.execute(
            select(Asset)
            .where(Asset.symbol.ilike(pattern) | Asset.name.ilike(pattern))
            .order_by(Asset.symbol)
            .limit(args.limit)
        ).scalars().all()

        headers = ["Símbolo", "Nome", "Tipo", "País"]
        rows = [
            (a.symbol, a.name[:35], a.asset_type.value if hasattr(a.asset_type, "value") else a.asset_type, a.country)
            for a in assets
        ]
        _table(headers, rows, [15, 35, 12, 8])
        print(f"\n  Encontrados: {len(rows)}")


def cmd_show(args):
    """Mostra detalhe de um símbolo."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, PriceDaily, FinancialStatement, ValuationMultiple

    _header(f"Detalhe: {args.symbol}")

    with get_session() as session:
        asset = session.execute(
            select(Asset).where(Asset.symbol == args.symbol)
        ).scalar_one_or_none()

        if not asset:
            _err(f"Asset '{args.symbol}' não encontrado")
            return

        print(f"  Símbolo:  {_c(asset.symbol, 'cyan')}")
        print(f"  Nome:     {asset.name}")
        atype = asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type
        print(f"  Tipo:     {atype}")
        print(f"  País:     {asset.country}")
        print(f"  Ativo:    {'Sim' if asset.is_active else 'Não'}")

        # Contagens
        price_count = session.execute(
            select(func.count(PriceDaily.id)).where(PriceDaily.asset_id == asset.id)
        ).scalar() or 0
        fin_count = session.execute(
            select(func.count(FinancialStatement.id)).where(FinancialStatement.asset_id == asset.id)
        ).scalar() or 0
        val_count = session.execute(
            select(func.count(ValuationMultiple.id)).where(ValuationMultiple.asset_id == asset.id)
        ).scalar() or 0

        print(f"\n  {_c('Dados no banco:', 'white')}")
        print(f"    Preços diários:    {price_count}")
        print(f"    Demonstrativos:    {fin_count}")
        print(f"    Valuations:        {val_count}")

        # Último preço
        price = session.execute(
            select(PriceDaily)
            .where(PriceDaily.asset_id == asset.id)
            .order_by(PriceDaily.date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if price:
            print(f"\n  {_c('Último preço:', 'white')}")
            print(f"    Data:    {price.date}")
            print(f"    Open:    {price.open}")
            print(f"    High:    {price.high}")
            print(f"    Low:     {price.low}")
            print(f"    Close:   {_c(str(price.close), 'cyan')}")
            if price.change_pct is not None:
                color = "green" if price.change_pct >= 0 else "red"
                print(f"    Var%:    {_c(f'{price.change_pct:+.2f}%', color)}")
            print(f"    Volume:  {price.volume}")


def cmd_prices(args):
    """Mostra preços recentes de um símbolo."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, PriceDaily
    from backend.api.prices import _parse_period

    _header(f"Preços: {args.symbol} ({args.period})")

    with get_session() as session:
        asset = session.execute(
            select(Asset).where(Asset.symbol == args.symbol)
        ).scalar_one_or_none()

        if not asset:
            _err(f"Asset '{args.symbol}' não encontrado")
            return

        start_date = _parse_period(args.period)
        prices = session.execute(
            select(PriceDaily)
            .where(PriceDaily.asset_id == asset.id, PriceDaily.date >= start_date)
            .order_by(PriceDaily.date.desc())
            .limit(args.limit)
        ).scalars().all()

        headers = ["Data", "Open", "High", "Low", "Close", "Change%", "Volume"]
        rows = [
            (
                str(p.date),
                f"{p.open:.2f}" if p.open else "—",
                f"{p.high:.2f}" if p.high else "—",
                f"{p.low:.2f}" if p.low else "—",
                f"{p.close:.2f}" if p.close else "—",
                p.change_pct if p.change_pct else 0,
                f"{p.volume:,.0f}" if p.volume else "—",
            )
            for p in prices
        ]
        _table(headers, rows, [12, 10, 10, 10, 10, 10, 14])
        print(f"\n  Total: {len(rows)} registros")


def cmd_top_movers(args):
    """Maiores altas e baixas."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, PriceDaily

    _header("Top Movers")

    with get_session() as session:
        # Subquery: última data com dados
        latest_date = session.execute(
            select(func.max(PriceDaily.date))
        ).scalar()

        if not latest_date:
            _err("Sem dados de preço no banco")
            return

        query = (
            select(Asset.symbol, Asset.name, PriceDaily.close, PriceDaily.change_pct, PriceDaily.date)
            .join(PriceDaily, PriceDaily.asset_id == Asset.id)
            .where(PriceDaily.date == latest_date, PriceDaily.change_pct.isnot(None))
        )

        if args.type:
            query = query.where(Asset.asset_type == args.type)
        if args.country:
            query = query.where(Asset.country == args.country.upper())

        # Maiores altas
        top_up = session.execute(
            query.order_by(PriceDaily.change_pct.desc()).limit(args.limit)
        ).fetchall()

        # Maiores baixas
        top_down = session.execute(
            query.order_by(PriceDaily.change_pct.asc()).limit(args.limit)
        ).fetchall()

        print(f"  Data de referência: {latest_date}\n")

        print(f"  {_c('MAIORES ALTAS', 'green')}")
        headers = ["Símbolo", "Nome", "Close", "Change%"]
        rows = [(r[0], r[1][:30], f"{r[2]:.2f}" if r[2] else "—", r[3]) for r in top_up]
        _table(headers, rows, [15, 30, 10, 10])

        print(f"\n  {_c('MAIORES BAIXAS', 'red')}")
        rows = [(r[0], r[1][:30], f"{r[2]:.2f}" if r[2] else "—", r[3]) for r in top_down]
        _table(headers, rows, [15, 30, 10, 10])


# ══════════════════════════════════════════════════════════
#  COMANDOS: GERENCIAMENTO
# ══════════════════════════════════════════════════════════

def cmd_add_asset(args):
    """Adiciona asset manualmente."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, AssetType

    _header("Adicionar Asset")

    # Validar tipo
    valid_types = [t.value for t in AssetType]
    if args.asset_type not in valid_types:
        _err(f"Tipo inválido: '{args.asset_type}'. Válidos: {', '.join(valid_types)}")
        return

    with get_session() as session:
        existing = session.execute(
            select(Asset).where(Asset.symbol == args.symbol)
        ).scalar_one_or_none()

        if existing:
            _err(f"Asset '{args.symbol}' já existe (id={existing.id})")
            return

        asset = Asset(
            symbol=args.symbol,
            name=args.name,
            asset_type=AssetType(args.asset_type),
            country=args.country.upper() if args.country else None,
        )
        session.add(asset)
        session.commit()
        _ok(f"Asset '{args.symbol}' criado com sucesso (id={asset.id})")


def cmd_remove_asset(args):
    """Desativa um asset (não deleta, apenas marca como inativo)."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset

    _header(f"Remover Asset: {args.symbol}")

    with get_session() as session:
        asset = session.execute(
            select(Asset).where(Asset.symbol == args.symbol)
        ).scalar_one_or_none()

        if not asset:
            _err(f"Asset '{args.symbol}' não encontrado")
            return

        if args.hard:
            if not args.force:
                resp = input(f"  {_c('ATENÇÃO:', 'red')} Deletar {args.symbol} e TODOS os dados? [s/N]: ")
                if resp.lower() not in ("s", "sim"):
                    _info("Cancelado")
                    return
            session.delete(asset)
            session.commit()
            _ok(f"Asset '{args.symbol}' e dados associados DELETADOS")
        else:
            asset.is_active = False
            session.commit()
            _ok(f"Asset '{args.symbol}' desativado (use --hard para deletar)")


def cmd_delete_prices(args):
    """Remove preços de um símbolo e/ou período."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, PriceDaily

    _header("Deletar Preços")

    with get_session() as session:
        asset = session.execute(
            select(Asset).where(Asset.symbol == args.symbol)
        ).scalar_one_or_none()

        if not asset:
            _err(f"Asset '{args.symbol}' não encontrado")
            return

        query = select(PriceDaily).where(PriceDaily.asset_id == asset.id)
        if args.start:
            query = query.where(PriceDaily.date >= args.start)
        if args.end:
            query = query.where(PriceDaily.date <= args.end)

        prices = session.execute(query).scalars().all()
        count = len(prices)

        if count == 0:
            _info("Nenhum preço encontrado com esses filtros")
            return

        if not args.force:
            resp = input(f"  Deletar {count} registros de preço de {args.symbol}? [s/N]: ")
            if resp.lower() not in ("s", "sim"):
                _info("Cancelado")
                return

        for p in prices:
            session.delete(p)
        session.commit()
        _ok(f"{count} registros de preço deletados")


def cmd_export(args):
    """Exporta dados para CSV."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, PriceDaily
    from backend.api.prices import _parse_period

    export_type = args.export_type  # "assets" ou "prices"

    _header(f"Exportar: {export_type}")

    output_file = args.output or f"export_{export_type}_{date.today().isoformat()}.csv"

    with get_session() as session:
        if export_type == "assets":
            query = select(Asset).where(Asset.is_active == True)
            if args.type:
                query = query.where(Asset.asset_type == args.type)
            if args.country:
                query = query.where(Asset.country == args.country.upper())
            query = query.order_by(Asset.symbol)

            assets = session.execute(query).scalars().all()

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["symbol", "name", "asset_type", "country", "is_active"])
                for a in assets:
                    atype = a.asset_type.value if hasattr(a.asset_type, "value") else a.asset_type
                    writer.writerow([a.symbol, a.name, atype, a.country, a.is_active])

            _ok(f"{len(assets)} assets exportados → {output_file}")

        elif export_type == "prices":
            if not args.symbol and not args.type and not args.country:
                _err("Especifique ao menos --symbol, --type ou --country para exportar preços")
                return

            query = (
                select(Asset.symbol, Asset.name, PriceDaily.date,
                       PriceDaily.open, PriceDaily.high, PriceDaily.low,
                       PriceDaily.close, PriceDaily.volume, PriceDaily.change_pct)
                .join(PriceDaily, PriceDaily.asset_id == Asset.id)
            )

            if args.symbol:
                query = query.where(Asset.symbol == args.symbol)
            if args.type:
                query = query.where(Asset.asset_type == args.type)
            if args.country:
                query = query.where(Asset.country == args.country.upper())
            if args.start:
                start_d = date.fromisoformat(args.start)
                query = query.where(PriceDaily.date >= start_d)
            if args.end:
                end_d = date.fromisoformat(args.end)
                query = query.where(PriceDaily.date <= end_d)

            query = query.order_by(Asset.symbol, PriceDaily.date)
            rows = session.execute(query).fetchall()

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["symbol", "name", "date", "open", "high", "low", "close", "volume", "change_pct"])
                for r in rows:
                    writer.writerow(list(r))

            _ok(f"{len(rows)} registros exportados → {output_file}")

        else:
            _err(f"Tipo de exportação inválido: '{export_type}'. Use 'assets' ou 'prices'")


# ══════════════════════════════════════════════════════════
#  PARSER DE ARGUMENTOS
# ══════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.cli",
        description="Market Platform Unified — CLI Versátil v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Comando a executar")

    # ── db-init ──
    p = sub.add_parser("db-init", help="Cria tabelas e popula assets")
    p.add_argument("--force", "-f", action="store_true", help="Pular confirmação se schema antigo for detectado")
    p.set_defaults(func=cmd_db_init)

    # ── db-status ──
    p = sub.add_parser("db-status", help="Mostra status do banco")
    p.set_defaults(func=cmd_db_status)

    # ── db-reset ──
    p = sub.add_parser("db-reset", help="Reset destrutivo do banco")
    p.add_argument("--force", "-f", action="store_true", help="Pular confirmação")
    p.set_defaults(func=cmd_db_reset)

    # ── Argumentos comuns de filtro ──
    def _add_filter_args(p, with_period=True, with_date=True, with_symbols=True):
        p.add_argument("--type", "-t", help="Tipo: stock, index, commodity, fx, crypto, etf")
        p.add_argument("--country", "-c", help="País: BR, US, GB, etc")
        if with_date:
            p.add_argument("--start", "-s", help="Data inicial (YYYY-MM-DD)")
            p.add_argument("--end", "-e", help="Data final (YYYY-MM-DD)")
        if with_period:
            p.add_argument("--period", "-p", default="1y", help="Período: 7d, 30d, 90d, 1y, etc (default: 1y)")
        if with_symbols:
            p.add_argument("--symbols", help="Lista de símbolos separados por vírgula")

    # ── ingest-prices ──
    p = sub.add_parser("ingest-prices", help="Ingere preços via yfinance")
    _add_filter_args(p)
    p.set_defaults(func=cmd_ingest_prices)

    # ── ingest-fundamentals ──
    p = sub.add_parser("ingest-fundamentals", help="Ingere fundamentos")
    _add_filter_args(p, with_period=False, with_date=False)
    p.set_defaults(func=cmd_ingest_fundamentals)

    # ── ingest-all ──
    p = sub.add_parser("ingest-all", help="Ingere preços + fundamentos")
    _add_filter_args(p)
    p.set_defaults(func=cmd_ingest_all)

    # ── list-assets ──
    p = sub.add_parser("list-assets", help="Lista assets")
    _add_filter_args(p, with_period=False, with_date=False, with_symbols=False)
    p.add_argument("--limit", "-l", type=int, default=50, help="Limite de resultados (default: 50)")
    p.set_defaults(func=cmd_list_assets)

    # ── search ──
    p = sub.add_parser("search", help="Busca assets por texto")
    p.add_argument("query", help="Texto para buscar (símbolo ou nome)")
    p.add_argument("--limit", "-l", type=int, default=20, help="Limite de resultados")
    p.set_defaults(func=cmd_search)

    # ── show ──
    p = sub.add_parser("show", help="Detalhe de um símbolo")
    p.add_argument("symbol", help="Símbolo (ex: PETR4.SA, AAPL)")
    p.set_defaults(func=cmd_show)

    # ── prices ──
    p = sub.add_parser("prices", help="Preços recentes de um símbolo")
    p.add_argument("symbol", help="Símbolo")
    p.add_argument("--period", "-p", default="30d", help="Período (default: 30d)")
    p.add_argument("--limit", "-l", type=int, default=30, help="Limite de registros")
    p.set_defaults(func=cmd_prices)

    # ── top-movers ──
    p = sub.add_parser("top-movers", help="Maiores altas e baixas")
    p.add_argument("--type", "-t", help="Filtrar por tipo")
    p.add_argument("--country", "-c", help="Filtrar por país")
    p.add_argument("--limit", "-l", type=int, default=10, help="Top N (default: 10)")
    p.set_defaults(func=cmd_top_movers)

    # ── add-asset ──
    p = sub.add_parser("add-asset", help="Adiciona um asset manualmente")
    p.add_argument("symbol", help="Ticker (ex: TICKER.SA)")
    p.add_argument("name", help="Nome do ativo")
    p.add_argument("asset_type", help="Tipo: stock, index, commodity, fx, crypto, etf")
    p.add_argument("country", nargs="?", default=None, help="País (BR, US, etc)")
    p.set_defaults(func=cmd_add_asset)

    # ── remove-asset ──
    p = sub.add_parser("remove-asset", help="Desativa/remove um asset")
    p.add_argument("symbol", help="Símbolo a remover")
    p.add_argument("--hard", action="store_true", help="Deletar permanentemente (com dados)")
    p.add_argument("--force", "-f", action="store_true", help="Pular confirmação")
    p.set_defaults(func=cmd_remove_asset)

    # ── delete-prices ──
    p = sub.add_parser("delete-prices", help="Remove preços de um símbolo")
    p.add_argument("symbol", help="Símbolo")
    p.add_argument("--start", "-s", help="Data inicial")
    p.add_argument("--end", "-e", help="Data final")
    p.add_argument("--force", "-f", action="store_true", help="Pular confirmação")
    p.set_defaults(func=cmd_delete_prices)

    # ── export ──
    p = sub.add_parser("export", help="Exporta dados para CSV")
    p.add_argument("export_type", choices=["assets", "prices"], help="O que exportar")
    p.add_argument("--symbol", help="Filtrar por símbolo (para prices)")
    p.add_argument("--type", "-t", help="Filtrar por tipo")
    p.add_argument("--country", "-c", help="Filtrar por país")
    p.add_argument("--start", "-s", help="Data inicial")
    p.add_argument("--end", "-e", help="Data final")
    p.add_argument("--output", "-o", help="Arquivo de saída (default: auto)")
    p.set_defaults(func=cmd_export)

    return parser


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print(f"\n  {_c('Exemplos:', 'yellow')}")
        print(f"    python -m backend.cli db-init")
        print(f"    python -m backend.cli ingest-prices --type stock --country BR --start 2025-01-01")
        print(f"    python -m backend.cli list-assets --type etf --country US")
        print(f"    python -m backend.cli show PETR4.SA")
        print(f"    python -m backend.cli top-movers --country BR")
        print(f"    python -m backend.cli export prices --country BR -o precos_br.csv")
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print(f"\n\n  {_c('Interrompido pelo usuário', 'yellow')}")
        sys.exit(1)
    except Exception as e:
        _err(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
