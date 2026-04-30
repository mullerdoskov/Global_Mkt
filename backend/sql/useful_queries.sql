-- ══════════════════════════════════════════════
-- QUERIES ÚTEIS PARA ANÁLISE
-- ══════════════════════════════════════════════

-- 1. Última data de atualização de preços por ativo
SELECT
    a.symbol,
    a.asset_type,
    MAX(pd.date) as last_price_date,
    COUNT(*) as price_records
FROM assets a
LEFT JOIN prices_daily pd ON a.id = pd.asset_id
GROUP BY a.id, a.symbol, a.asset_type
ORDER BY a.symbol;


-- 2. Ativos com dados faltando (mais de 1 dia sem atualização)
SELECT
    a.symbol,
    MAX(pd.date) as last_price_date,
    CURRENT_DATE - MAX(pd.date) as days_since_update
FROM assets a
LEFT JOIN prices_daily pd ON a.id = pd.asset_id
GROUP BY a.id, a.symbol
HAVING CURRENT_DATE - MAX(pd.date) > 1
ORDER BY days_since_update DESC;


-- 3. Retorno acumulado por ativo (últimos 90 dias)
WITH first_price AS (
    SELECT
        asset_id,
        close as first_close,
        ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY date ASC) as rn
    FROM prices_daily
    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
),
last_price AS (
    SELECT
        asset_id,
        close as last_close,
        ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY date DESC) as rn
    FROM prices_daily
    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT
    a.symbol,
    fp.first_close,
    lp.last_close,
    ROUND((lp.last_close / fp.first_close - 1) * 100, 2) as return_pct_90d
FROM assets a
JOIN first_price fp ON a.id = fp.asset_id AND fp.rn = 1
JOIN last_price lp ON a.id = lp.asset_id AND lp.rn = 1
ORDER BY return_pct_90d DESC;


-- 4. Média de volume por ativo (últimos 30 dias)
SELECT
    a.symbol,
    a.name,
    COUNT(*) as trading_days,
    ROUND(AVG(CAST(pd.volume AS DECIMAL)), 0) as avg_volume_30d,
    MAX(pd.volume) as max_volume_30d,
    MIN(pd.volume) as min_volume_30d
FROM assets a
LEFT JOIN prices_daily pd ON a.id = pd.asset_id
    AND pd.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY a.id, a.symbol, a.name
ORDER BY avg_volume_30d DESC NULLS LAST;


-- 5. Evolução de preços (últimos 10 pregões)
SELECT
    a.symbol,
    pd.date,
    pd.open,
    pd.high,
    pd.low,
    pd.close,
    pd.volume,
    LAG(pd.close) OVER (PARTITION BY a.id ORDER BY pd.date) as prev_close,
    ROUND((pd.close / LAG(pd.close) OVER (PARTITION BY a.id ORDER BY pd.date) - 1) * 100, 2) as daily_return_pct
FROM assets a
JOIN prices_daily pd ON a.id = pd.asset_id
WHERE a.symbol = 'PETR3.SA'  -- Substituir pelo símbolo desejado
ORDER BY pd.date DESC
LIMIT 10;


-- 6. Status de ingestão por tipo de ativo
SELECT
    asset_type,
    COUNT(*) as total_assets,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_assets,
    MAX(
        SELECT MAX(pd.date)
        FROM prices_daily pd
        WHERE pd.asset_id = a.id
    ) as latest_update
FROM assets a
GROUP BY asset_type
ORDER BY asset_type;


-- 7. Erros de ingestão recentes
SELECT
    symbol,
    ingestion_type,
    started_at,
    error_message,
    duration_seconds
FROM ingestion_log
WHERE status = 'error'
ORDER BY started_at DESC
LIMIT 20;


-- 8. Performance por setor (retorno médio, últimos 90 dias)
WITH sector_returns AS (
    SELECT
        sg.sector,
        sg.sector_pt,
        c.id as company_id,
        a.id as asset_id,
        pd.date,
        pd.close,
        LAG(pd.close) OVER (PARTITION BY a.id ORDER BY pd.date) as prev_close,
        (pd.close / LAG(pd.close) OVER (PARTITION BY a.id ORDER BY pd.date) - 1) as daily_ret
    FROM sectors_gics sg
    JOIN companies c ON sg.id = c.sector_gics_id
    JOIN assets a ON c.id = a.company_id
    LEFT JOIN prices_daily pd ON a.id = pd.asset_id
        AND pd.date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT
    sector,
    sector_pt,
    COUNT(DISTINCT company_id) as companies,
    COUNT(DISTINCT asset_id) as assets,
    ROUND(AVG(daily_ret) * 100, 4) as avg_daily_return_pct,
    ROUND(STDDEV(daily_ret) * 100, 4) as volatility_pct
FROM sector_returns
WHERE daily_ret IS NOT NULL
GROUP BY sector, sector_pt
ORDER BY avg_daily_return_pct DESC;


-- 9. Ativos sem dados financeiros
SELECT
    c.ticker,
    c.name,
    COUNT(fs.id) as financial_records,
    COUNT(vm.id) as valuation_records
FROM companies c
LEFT JOIN financial_statements fs ON c.id = fs.company_id
LEFT JOIN valuation_multiples vm ON c.id = vm.company_id
GROUP BY c.id, c.ticker, c.name
HAVING COUNT(fs.id) = 0 OR COUNT(vm.id) = 0
ORDER BY c.ticker;


-- 10. Distribuição de ativos por país e setor
SELECT
    co.iso2 as country,
    co.name as country_name,
    sg.sector,
    COUNT(DISTINCT a.id) as asset_count
FROM assets a
LEFT JOIN companies c ON a.company_id = c.id
LEFT JOIN countries co ON c.country_id = co.id
LEFT JOIN sectors_gics sg ON c.sector_gics_id = sg.id
WHERE a.is_active = true
GROUP BY co.iso2, co.name, sg.sector
ORDER BY co.iso2, sg.sector;
