-- DeepSnow Stock Pool Database Schema
-- Independent SQLite database for investment research data persistence

-- Main stock pool table
CREATE TABLE IF NOT EXISTS stocks (
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'A',  -- 'A' / 'HK' / 'US'
    sector TEXT NOT NULL,              -- 'tech' / 'consumer' / 'pharma' / 'cyclical' / 'high_dividend'
    pool_tier TEXT NOT NULL DEFAULT 'reserve',  -- 'core' / 'satellite' / 'watch' / 'reserve'
    company_type TEXT,                 -- 'tree' / 'grain' / 'vegetable'
    business_model TEXT,
    industry_cycle TEXT,               -- 'spring' / 'summer' / 'autumn' / 'winter'
    build_phase TEXT NOT NULL DEFAULT 'phase0',  -- 'phase0' / 'phase1' / 'phase2' / 'phase3'
    price_value_state TEXT,            -- 'no_reaction' / 'reasonable' / 'over_optimistic' / 'over_pessimistic'
    consensus_stage TEXT,              -- 'stage1' / 'stage2' / 'stage3'
    rating TEXT,                       -- 'strong_buy' / 'buy' / 'accumulate' / 'neutral' / 'reduce' / 'sell'
    great_total INTEGER,
    target_price_conservative REAL,
    target_price_neutral REAL,
    target_price_optimistic REAL,
    buy_company_test TEXT,             -- One-sentence answer: would you buy the whole company?
    one_line_thesis TEXT,              -- Why hold this stock in one sentence
    tracking_points TEXT,              -- JSON array of 3-5 key tracking indicators
    sell_signals TEXT,                 -- JSON array of 3-5 sell trigger conditions
    last_report_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (code, market)
);

-- GREAT scores history (allows tracking score evolution over time)
CREATE TABLE IF NOT EXISTS great_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_market TEXT NOT NULL DEFAULT 'A',
    scored_at TEXT NOT NULL DEFAULT (datetime('now')),
    growth INTEGER NOT NULL,
    growth_note TEXT,
    replicable INTEGER NOT NULL,
    replicable_note TEXT,
    potential INTEGER NOT NULL,
    potential_note TEXT,
    excellent INTEGER NOT NULL,
    excellent_note TEXT,
    return_certainty INTEGER NOT NULL,
    return_note TEXT,
    total INTEGER GENERATED ALWAYS AS (growth + replicable + potential + excellent + return_certainty) STORED,
    FOREIGN KEY (stock_code, stock_market) REFERENCES stocks(code, market)
);

-- Tracking log: all state changes with reasons (audit trail)
CREATE TABLE IF NOT EXISTS tracking_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_market TEXT NOT NULL DEFAULT 'A',
    logged_at TEXT NOT NULL DEFAULT (datetime('now')),
    event_type TEXT NOT NULL,  -- 'tier_change' / 'phase_change' / 'rating_change' / 'price_value_change' / 'great_update' / 'report' / 'note'
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    FOREIGN KEY (stock_code, stock_market) REFERENCES stocks(code, market)
);

-- Decision log: all investment decisions with rationale for quarterly review
CREATE TABLE IF NOT EXISTS decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decided_at TEXT NOT NULL DEFAULT (datetime('now')),
    decision_type TEXT NOT NULL,  -- 'buy' / 'add' / 'reduce' / 'sell' / 'pool_change' / 'phase_advance'
    stock_code TEXT,
    stock_market TEXT,
    content TEXT NOT NULL,
    build_phase TEXT,
    rationale TEXT NOT NULL,
    data_snapshot TEXT,             -- JSON: key data at time of decision
    expected_outcome TEXT,
    review_date TEXT,               -- When to review this decision
    actual_outcome TEXT,            -- Filled during quarterly review
    deviation_attribution TEXT      -- 'season_wrong' / 'company_wrong' / 'position_wrong' / 'execution_wrong' / 'discipline_violation' / 'luck'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stocks_sector ON stocks(sector);
CREATE INDEX IF NOT EXISTS idx_stocks_tier ON stocks(pool_tier);
CREATE INDEX IF NOT EXISTS idx_stocks_phase ON stocks(build_phase);
CREATE INDEX IF NOT EXISTS idx_great_scores_stock ON great_scores(stock_code, stock_market);
CREATE INDEX IF NOT EXISTS idx_tracking_log_stock ON tracking_log(stock_code, stock_market);
CREATE INDEX IF NOT EXISTS idx_decision_log_date ON decision_log(decided_at);
