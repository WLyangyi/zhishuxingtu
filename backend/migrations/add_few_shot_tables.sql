-- 提示词工程进阶模块数据库迁移
-- 创建时间: 2026-03-20
-- 版本: v1.9.0

-- Few-Shot示例表
CREATE TABLE IF NOT EXISTS few_shot_examples (
    id VARCHAR(36) PRIMARY KEY,
    prompt_id VARCHAR(36),
    scenario VARCHAR(50) NOT NULL,
    input_example TEXT NOT NULL,
    output_example TEXT NOT NULL,
    quality_score REAL DEFAULT 5.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

-- 提示词版本表
CREATE TABLE IF NOT EXISTS prompt_versions (
    id VARCHAR(36) PRIMARY KEY,
    prompt_id VARCHAR(36) NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    version_name VARCHAR(100),
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT,
    changes_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

-- A/B实验表
CREATE TABLE IF NOT EXISTS ab_experiments (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    prompt_id VARCHAR(36) NOT NULL,
    version_a_id VARCHAR(36) NOT NULL,
    version_b_id VARCHAR(36) NOT NULL,
    traffic_split REAL DEFAULT 0.5,
    status VARCHAR(20) DEFAULT 'running',
    start_time DATETIME,
    end_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id),
    FOREIGN KEY (version_a_id) REFERENCES prompt_versions(id),
    FOREIGN KEY (version_b_id) REFERENCES prompt_versions(id)
);

-- A/B测试结果表
CREATE TABLE IF NOT EXISTS ab_test_results (
    id VARCHAR(36) PRIMARY KEY,
    experiment_id VARCHAR(36) NOT NULL,
    version_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36),
    user_question TEXT,
    ai_response TEXT,
    response_time_ms VARCHAR(20),
    token_count VARCHAR(20),
    user_feedback VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experiment_id) REFERENCES ab_experiments(id),
    FOREIGN KEY (version_id) REFERENCES prompt_versions(id)
);

-- 提示词评估表
CREATE TABLE IF NOT EXISTS prompt_evaluations (
    id VARCHAR(36) PRIMARY KEY,
    prompt_version_id VARCHAR(36),
    session_id VARCHAR(36),
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    context TEXT,
    relevance_score REAL,
    accuracy_score REAL,
    completeness_score REAL,
    clarity_score REAL,
    overall_score REAL,
    response_time_ms VARCHAR(20),
    token_count VARCHAR(20),
    cost_usd REAL DEFAULT 0.0,
    user_rating VARCHAR(10),
    user_feedback TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_version_id) REFERENCES prompt_versions(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_few_shot_scenario ON few_shot_examples(scenario);
CREATE INDEX IF NOT EXISTS idx_few_shot_prompt ON few_shot_examples(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt ON prompt_versions(prompt_id);
CREATE INDEX IF NOT EXISTS idx_ab_experiments_prompt ON ab_experiments(prompt_id);
CREATE INDEX IF NOT EXISTS idx_ab_experiments_status ON ab_experiments(status);
CREATE INDEX IF NOT EXISTS idx_ab_test_results_experiment ON ab_test_results(experiment_id);
CREATE INDEX IF NOT EXISTS idx_prompt_evaluations_version ON prompt_evaluations(prompt_version_id);
CREATE INDEX IF NOT EXISTS idx_prompt_evaluations_score ON prompt_evaluations(overall_score);
