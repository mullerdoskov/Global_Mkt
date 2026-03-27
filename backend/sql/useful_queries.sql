-- ═══════════════════════════════════════════════════════════
--  Market Platform Unified — Queries Analíticas
-- ═══════════════════════════════════════════════════════════

-- 1. Contagem geral por tabela
SELECT 'assets' AS tabela, COUNT(*) FROM assets
UNION ALL SELECT 'prices_daily', COUNT(*) FROM prices_daily
UNION ALL SELECT 'financial_statements', COUNT(*) FROM financial_statements
UNION ALL SELECT 'valuation_multiples', COUNT(*) FROM valuation_multiples
UNION ALL SELECT 'ingestion_log', COUNT(*) FROM ingestion_log;

-- 2. Assets por tipo e país
SELECT asset_type, country, COUNT(*)
FROM assets
WHERE is_active = true
GROUP BY asset_type, country
ORDER BY COUNT(*) DESC;

-- 3. Último preço de cada ativo (fix com DISTINCT ON para PostgreSQL)
SELECT DISTINCT ON (a.id)
    a.symbol, a.name, a.asset_type::text, p.close, p.change_pct, p.date
FROM assets a
JOIN prices_daily p ON p.asset_id = a.id
ORDER BY a.id, p.date DESC;

-- 4. Top 10 maiores altas do último dia com dados
SELECT a.symbol, a.name, p.close, p.change_pct
FROM prices_daily p
JOIN assets a ON a.id = p.asset_id
WHERE p.date = (SELECT MAX(date) FROM prices_daily)
  AND p.change_pct IS NOT NULL
ORDER BY p.change_pct DESC
LIMIT 10;

-- 5. Top 10 maiores quedas
SELECT a.symbol, a.name, p.close, p.change_pct
FROM prices_daily p
JOIN assets a ON a.id = p.asset_id
WHERE p.date = (SELECT MAX(date) FROM prices_daily)
  AND p.change_pct IS NOT NULL
ORDER BY p.change_pct ASC
LIMIT 10;

-- 6. Volume médio por tipo de ativo (últimos 30 dias)
SELECT a.asset_type::text, AVG(p.volume) AS avg_volume, COUNT(DISTINCT a.id) AS assets
FROM prices_daily p
JOIN assets a ON a.id = p.asset_id
WHERE p.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY a.asset_type
ORDER BY avg_volume DESC;

-- 7. Ativos sem dados de preço
SELECT a.symbol, a.name, a.asset_type::text, a.country
FROM assets a
LEFT JOIN prices_daily p ON p.asset_id = a.id
WHERE p.id IS NULL AND a.is_active = true
ORDER BY a.symbol;

-- 8. Range de datas por ativo
SELECT a.symbol, MIN(p.date) AS first_date, MAX(p.date) AS last_date, COUNT(*) AS total_days
FROM prices_daily p
JOIN assets a ON a.id = p.asset_id
GROUP BY a.symbol
ORDER BY total_days DESC
LIMIT 20;

-- 9. Stocks brasileiras com melhor dividend yield
SELECT a.symbol, a.name, v.dividend_yield, v.pe_ratio, v.market_cap
FROM valuation_multiples v
JOIN assets a ON a.id = v.asset_id
WHERE a.country = 'BR' AND a.asset_type = 'stock'
  AND v.dividend_yield IS NOT NULL
  AND v.date = (SELECT MAX(v2.date) FROM valuation_multiples v2 WHERE v2.asset_id = v.asset_id)
ORDER BY v.dividend_yield DESC
LIMIT 20;

-- 10. Resumo de ingestão (últimas 24h)
SELECT
    il.status::text,
    il.data_type,
    COUNT(*) AS total,
    SUM(il.rows_inserted) AS inserted,
    SUM(il.rows_updated) AS updated
FROM ingestion_log il
WHERE il.started_at >= NOW() - INTERVAL '24 hours'
GROUP BY il.status, il.data_type
ORDER BY total DESC;

-- 11. Correlação diária entre dois ativos (ex: PETR4 vs Brent)
SELECT
    p1.date,
    p1.change_pct AS petr4_pct,
    p2.change_pct AS brent_pct
FROM prices_daily p1
JOIN assets a1 ON a1.id = p1.asset_id AND a1.symbol = 'PETR4.SA'
JOIN prices_daily p2 ON p2.date = p1.date
JOIN assets a2 ON a2.id = p2.asset_id AND a2.symbol = 'BZ=F'
WHERE p1.date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY p1.date;
