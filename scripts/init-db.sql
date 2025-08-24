-- Database initialization script for Momentum Lens ETF trading system
-- This script sets up the initial database schema with TimescaleDB extensions

\c momentum_lens;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable additional useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas for organization
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS system;

-- Set search path
SET search_path = public, market_data, trading, analytics, system;

-- Create users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create ETF information table
CREATE TABLE IF NOT EXISTS market_data.etf_info (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    underlying_index VARCHAR(255),
    expense_ratio DECIMAL(5,4),
    inception_date DATE,
    exchange VARCHAR(20),
    currency VARCHAR(3) DEFAULT 'CNY',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create price history table (will be converted to hypertable)
CREATE TABLE IF NOT EXISTS market_data.price_history (
    time TIMESTAMPTZ NOT NULL,
    etf_code VARCHAR(20) NOT NULL REFERENCES market_data.etf_info(code),
    open_price DECIMAL(10,4),
    high_price DECIMAL(10,4),
    low_price DECIMAL(10,4),
    close_price DECIMAL(10,4) NOT NULL,
    volume BIGINT,
    turnover DECIMAL(15,2),
    prev_close DECIMAL(10,4),
    change_pct DECIMAL(8,4),
    PRIMARY KEY (time, etf_code)
);

-- Convert price_history to hypertable
SELECT create_hypertable('market_data.price_history', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create real-time price table for latest prices
CREATE TABLE IF NOT EXISTS market_data.real_time_prices (
    etf_code VARCHAR(20) PRIMARY KEY REFERENCES market_data.etf_info(code),
    price DECIMAL(10,4) NOT NULL,
    change_pct DECIMAL(8,4),
    volume BIGINT,
    turnover DECIMAL(15,2),
    bid_price DECIMAL(10,4),
    ask_price DECIMAL(10,4),
    bid_volume INTEGER,
    ask_volume INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create portfolio table
CREATE TABLE IF NOT EXISTS trading.portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    name VARCHAR(255) NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    current_capital DECIMAL(15,2) NOT NULL,
    available_cash DECIMAL(15,2) NOT NULL,
    total_market_value DECIMAL(15,2) DEFAULT 0,
    total_return DECIMAL(10,4) DEFAULT 0,
    total_return_pct DECIMAL(8,4) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create holdings table
CREATE TABLE IF NOT EXISTS trading.holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES trading.portfolios(id),
    etf_code VARCHAR(20) NOT NULL REFERENCES market_data.etf_info(code),
    quantity INTEGER NOT NULL,
    avg_cost DECIMAL(10,4) NOT NULL,
    current_price DECIMAL(10,4),
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    unrealized_pnl_pct DECIMAL(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(portfolio_id, etf_code)
);

-- Create trading orders table
CREATE TABLE IF NOT EXISTS trading.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES trading.portfolios(id),
    etf_code VARCHAR(20) NOT NULL REFERENCES market_data.etf_info(code),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('BUY', 'SELL')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' 
        CHECK (status IN ('PENDING', 'FILLED', 'CANCELLED', 'PARTIALLY_FILLED', 'FAILED')),
    quantity INTEGER NOT NULL,
    price DECIMAL(10,4),
    filled_quantity INTEGER DEFAULT 0,
    filled_price DECIMAL(10,4),
    commission DECIMAL(10,4) DEFAULT 0,
    strategy VARCHAR(50),
    signal_strength DECIMAL(5,4),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Create trading signals table (hypertable for time-series data)
CREATE TABLE IF NOT EXISTS analytics.trading_signals (
    time TIMESTAMPTZ NOT NULL,
    etf_code VARCHAR(20) NOT NULL REFERENCES market_data.etf_info(code),
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    strategy VARCHAR(50) NOT NULL,
    strength DECIMAL(5,4) NOT NULL,
    confidence DECIMAL(5,4),
    parameters JSONB,
    indicators JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, etf_code, strategy)
);

-- Convert trading_signals to hypertable
SELECT create_hypertable('analytics.trading_signals', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create momentum scores table (hypertable)
CREATE TABLE IF NOT EXISTS analytics.momentum_scores (
    time TIMESTAMPTZ NOT NULL,
    etf_code VARCHAR(20) NOT NULL REFERENCES market_data.etf_info(code),
    momentum_1d DECIMAL(8,4),
    momentum_5d DECIMAL(8,4),
    momentum_10d DECIMAL(8,4),
    momentum_20d DECIMAL(8,4),
    momentum_60d DECIMAL(8,4),
    volatility DECIMAL(8,4),
    volume_ratio DECIMAL(8,4),
    rsi DECIMAL(8,4),
    macd DECIMAL(8,4),
    composite_score DECIMAL(8,4),
    rank_score INTEGER,
    PRIMARY KEY (time, etf_code)
);

-- Convert momentum_scores to hypertable
SELECT create_hypertable('analytics.momentum_scores', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create system configuration table
CREATE TABLE IF NOT EXISTS system.configurations (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create system logs table (hypertable)
CREATE TABLE IF NOT EXISTS system.logs (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,
    logger VARCHAR(100),
    message TEXT NOT NULL,
    module VARCHAR(100),
    function VARCHAR(100),
    line_number INTEGER,
    extra JSONB,
    PRIMARY KEY (time, level)
);

-- Convert logs to hypertable
SELECT create_hypertable('system.logs', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create performance metrics table (hypertable)
CREATE TABLE IF NOT EXISTS analytics.performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    portfolio_id UUID NOT NULL REFERENCES trading.portfolios(id),
    total_return DECIMAL(10,4),
    daily_return DECIMAL(10,4),
    volatility DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(5,4),
    profit_factor DECIMAL(8,4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    PRIMARY KEY (time, portfolio_id)
);

-- Convert performance_metrics to hypertable
SELECT create_hypertable('analytics.performance_metrics', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create indexes for better query performance

-- Market data indexes
CREATE INDEX IF NOT EXISTS idx_price_history_code_time ON market_data.price_history(etf_code, time DESC);
CREATE INDEX IF NOT EXISTS idx_real_time_prices_timestamp ON market_data.real_time_prices(timestamp DESC);

-- Trading indexes
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio_id ON trading.holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_orders_portfolio_id ON trading.orders(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON trading.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON trading.orders(created_at DESC);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_code_time ON analytics.trading_signals(etf_code, time DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_strategy ON analytics.trading_signals(strategy);
CREATE INDEX IF NOT EXISTS idx_momentum_scores_time_score ON analytics.momentum_scores(time DESC, composite_score DESC);

-- System indexes
CREATE INDEX IF NOT EXISTS idx_logs_time_level ON system.logs(time DESC, level);
CREATE INDEX IF NOT EXISTS idx_configs_key ON system.configurations(key);

-- Create triggers for updating timestamps

-- Update trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_etf_info_updated_at BEFORE UPDATE ON market_data.etf_info
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON trading.portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_holdings_updated_at BEFORE UPDATE ON trading.holdings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON system.configurations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create continuous aggregates for common queries

-- Daily OHLC aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data.daily_ohlc
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS day,
       etf_code,
       FIRST(open_price, time) AS open_price,
       MAX(high_price) AS high_price,
       MIN(low_price) AS low_price,
       LAST(close_price, time) AS close_price,
       SUM(volume) AS volume,
       SUM(turnover) AS turnover
FROM market_data.price_history
GROUP BY day, etf_code;

-- Hourly trading signal summary
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.hourly_signals
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS hour,
       etf_code,
       strategy,
       signal_type,
       AVG(strength) AS avg_strength,
       COUNT(*) AS signal_count
FROM analytics.trading_signals
GROUP BY hour, etf_code, strategy, signal_type;

-- Set up data retention policies (keep data for 2 years)
SELECT add_retention_policy('market_data.price_history', INTERVAL '2 years');
SELECT add_retention_policy('analytics.trading_signals', INTERVAL '2 years');
SELECT add_retention_policy('analytics.momentum_scores', INTERVAL '2 years');
SELECT add_retention_policy('system.logs', INTERVAL '90 days');
SELECT add_retention_policy('analytics.performance_metrics', INTERVAL '2 years');

-- Insert initial ETF data
INSERT INTO market_data.etf_info (code, name, category, underlying_index, expense_ratio, inception_date, exchange) VALUES
('510300', '沪深300ETF', '宽基指数', '沪深300', 0.0050, '2012-05-28', 'SSE'),
('510500', '中证500ETF', '宽基指数', '中证500', 0.0050, '2013-03-25', 'SSE'),
('159915', '创业板ETF', '宽基指数', '创业板指', 0.0050, '2011-09-20', 'SZSE'),
('512000', '券商ETF', '行业指数', '中证全指证券公司', 0.0050, '2015-04-17', 'SSE'),
('512100', '医药ETF', '行业指数', '中证医药', 0.0050, '2013-09-25', 'SSE'),
('515050', '5G ETF', '主题指数', '中证5G通信主题', 0.0050, '2019-09-19', 'SSE'),
('516160', '新能源ETF', '主题指数', '中证新能源', 0.0050, '2021-01-27', 'SSE'),
('588000', '科创50ETF', '宽基指数', '科创50', 0.0050, '2020-09-22', 'SSE'),
('159949', '创业板50ETF', '宽基指数', '创业板50', 0.0050, '2016-05-11', 'SZSE'),
('515880', '通信ETF', '行业指数', '中证通信设备', 0.0050, '2020-01-20', 'SSE')
ON CONFLICT (code) DO NOTHING;

-- Insert default system configurations
INSERT INTO system.configurations (key, value, description) VALUES
('trading_enabled', 'true', 'Whether trading is enabled'),
('market_hours', '{"start": "09:30", "end": "15:00", "timezone": "Asia/Shanghai"}', 'Market trading hours'),
('execution_windows', '["10:30", "14:00"]', 'Preferred execution time windows'),
('risk_limits', '{"max_position_size": 0.1, "max_daily_trades": 20, "stop_loss": 0.05}', 'Risk management limits'),
('momentum_thresholds', '{"buy": 0.7, "sell": 0.3, "hold_min": 0.4, "hold_max": 0.6}', 'Momentum signal thresholds'),
('default_preset', 'balanced', 'Default trading strategy preset')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Grant permissions
GRANT USAGE ON SCHEMA market_data TO momentum_user;
GRANT USAGE ON SCHEMA trading TO momentum_user;
GRANT USAGE ON SCHEMA analytics TO momentum_user;
GRANT USAGE ON SCHEMA system TO momentum_user;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO momentum_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA market_data TO momentum_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading TO momentum_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO momentum_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA system TO momentum_user;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO momentum_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA system TO momentum_user;

-- Create database statistics view for monitoring
CREATE VIEW system.database_stats AS
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY schemaname, tablename;

COMMIT;