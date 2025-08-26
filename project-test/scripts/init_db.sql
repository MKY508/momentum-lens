-- Database initialization script for Momentum Lens

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create schema
CREATE SCHEMA IF NOT EXISTS momentum;

-- Set default search path
SET search_path TO momentum, public;

-- ETF daily price data
CREATE TABLE IF NOT EXISTS etf_daily_prices (
    code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(10, 4),
    high DECIMAL(10, 4),
    low DECIMAL(10, 4),
    close DECIMAL(10, 4) NOT NULL,
    volume BIGINT,
    turnover DECIMAL(20, 2),
    change_pct DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code, date)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('etf_daily_prices', 'date', 
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);

-- ETF metadata
CREATE TABLE IF NOT EXISTS etf_metadata (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50),
    sector VARCHAR(50),
    inception_date DATE,
    management_fee DECIMAL(5, 4),
    tracking_index VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolio positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    module VARCHAR(20) NOT NULL CHECK (module IN ('core', 'satellite', 'convertible')),
    shares DECIMAL(15, 2) NOT NULL,
    avg_cost DECIMAL(10, 4) NOT NULL,
    entry_date DATE NOT NULL,
    exit_date DATE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trading decisions log
CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    decision_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    module VARCHAR(20) NOT NULL,
    signal VARCHAR(20) NOT NULL,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    target_weight DECIMAL(5, 4),
    current_weight DECIMAL(5, 4),
    action_amount DECIMAL(15, 2),
    reason TEXT,
    priority INTEGER,
    metadata JSONB,
    executed BOOLEAN DEFAULT FALSE,
    execution_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Convert to hypertable
SELECT create_hypertable('decisions', 'decision_time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);

-- Market environment snapshots
CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    market_state VARCHAR(20),
    ma200_ratio DECIMAL(8, 4),
    atr20 DECIMAL(8, 6),
    chop DECIMAL(8, 2),
    vix_level VARCHAR(10),
    metadata JSONB,
    PRIMARY KEY (snapshot_time)
);

-- Convert to hypertable
SELECT create_hypertable('market_snapshots', 'snapshot_time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE);

-- Momentum scores
CREATE TABLE IF NOT EXISTS momentum_scores (
    score_date DATE NOT NULL,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    r3m DECIMAL(8, 4),
    r6m DECIMAL(8, 4),
    total_score DECIMAL(8, 4),
    rank INTEGER,
    ma200_state VARCHAR(20),
    atr20 DECIMAL(8, 6),
    chop DECIMAL(8, 2),
    volume_ratio DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (score_date, code)
);

-- Convert to hypertable
SELECT create_hypertable('momentum_scores', 'score_date',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);

-- Convertible bonds data
CREATE TABLE IF NOT EXISTS convertible_bonds (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    conversion_price DECIMAL(10, 4),
    premium_rate DECIMAL(8, 4),
    balance DECIMAL(20, 2),
    remaining_years DECIMAL(5, 2),
    rating VARCHAR(10),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DCA execution plan
CREATE TABLE IF NOT EXISTS dca_plan (
    week_number INTEGER PRIMARY KEY,
    execution_date DATE NOT NULL,
    target_amount DECIMAL(15, 2) NOT NULL,
    executed_amount DECIMAL(15, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'skipped')),
    allocations JSONB,
    execution_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_date DATE PRIMARY KEY,
    total_value DECIMAL(20, 2),
    total_cost DECIMAL(20, 2),
    daily_return DECIMAL(8, 6),
    cumulative_return DECIMAL(8, 6),
    sharpe_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(8, 6),
    win_rate DECIMAL(5, 4),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Risk alerts
CREATE TABLE IF NOT EXISTS risk_alerts (
    id SERIAL PRIMARY KEY,
    alert_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    code VARCHAR(10),
    message TEXT NOT NULL,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_etf_daily_prices_code ON etf_daily_prices(code);
CREATE INDEX idx_etf_daily_prices_date ON etf_daily_prices(date DESC);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_module ON positions(module);
CREATE INDEX idx_decisions_executed ON decisions(executed);
CREATE INDEX idx_decisions_code ON decisions(code);
CREATE INDEX idx_momentum_scores_rank ON momentum_scores(rank);
CREATE INDEX idx_risk_alerts_acknowledged ON risk_alerts(acknowledged);

-- Create views for common queries

-- Current positions view
CREATE OR REPLACE VIEW v_current_positions AS
SELECT 
    p.*,
    edp.close as current_price,
    p.shares * edp.close as market_value,
    (edp.close - p.avg_cost) * p.shares as unrealized_pnl,
    (edp.close - p.avg_cost) / p.avg_cost as unrealized_pnl_pct
FROM positions p
LEFT JOIN LATERAL (
    SELECT close 
    FROM etf_daily_prices 
    WHERE code = p.code 
    ORDER BY date DESC 
    LIMIT 1
) edp ON true
WHERE p.status = 'active';

-- Latest momentum rankings view
CREATE OR REPLACE VIEW v_latest_momentum AS
SELECT *
FROM momentum_scores
WHERE score_date = (SELECT MAX(score_date) FROM momentum_scores)
ORDER BY rank;

-- Portfolio summary view
CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT 
    COUNT(*) as position_count,
    SUM(market_value) as total_value,
    SUM(shares * avg_cost) as total_cost,
    SUM(unrealized_pnl) as total_unrealized_pnl,
    AVG(unrealized_pnl_pct) as avg_return,
    COUNT(CASE WHEN module = 'core' THEN 1 END) as core_count,
    COUNT(CASE WHEN module = 'satellite' THEN 1 END) as satellite_count,
    COUNT(CASE WHEN module = 'convertible' THEN 1 END) as convertible_count
FROM v_current_positions;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA momentum TO momentum_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA momentum TO momentum_user;
GRANT ALL PRIVILEGES ON SCHEMA momentum TO momentum_user;