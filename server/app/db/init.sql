-- ══════════════════════════════════════════════
--  TalkPC SaaS - 전체 DDL
-- ══════════════════════════════════════════════

-- 1. 사용자
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) DEFAULT '',
    email VARCHAR(100) DEFAULT '',
    role VARCHAR(10) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. 크레딧 (충전/사용/보너스)
CREATE TABLE IF NOT EXISTS credits (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    amount INT NOT NULL,
    type VARCHAR(10) NOT NULL,
    description VARCHAR(200) DEFAULT '',
    admin_id INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_credits_user ON credits(user_id, created_at);

-- 3. 연락처 (사용자별)
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    category VARCHAR(20) DEFAULT 'other',
    phone VARCHAR(20) DEFAULT '',
    company VARCHAR(50) DEFAULT '',
    position VARCHAR(30) DEFAULT '',
    memo VARCHAR(200) DEFAULT '',
    birthday VARCHAR(5) DEFAULT '',
    anniversary VARCHAR(5) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sent TIMESTAMP,
    send_count INT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id);

-- 4. 템플릿 (사용자별)
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(20) DEFAULT 'all',
    contents JSONB NOT NULL DEFAULT '[]',
    image_path VARCHAR(500) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id);

-- 5. 발송 로그
CREATE TABLE IF NOT EXISTS send_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    contact_id INT,
    contact_name VARCHAR(50) DEFAULT '',
    contact_phone VARCHAR(20) DEFAULT '',
    msg_type VARCHAR(10) NOT NULL,
    message_preview VARCHAR(100) DEFAULT '',
    mseq INT,
    status VARCHAR(20) DEFAULT 'queued',
    cost INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_send_logs_user ON send_logs(user_id, created_at);

-- ══════════════════════════════════════════════
--  세종텔레콤 MessagingAgent 테이블 (PostgreSQL)
-- ══════════════════════════════════════════════

-- msg_queue 시퀀스
CREATE SEQUENCE IF NOT EXISTS msg_queue_seq INCREMENT 1 START 1 MAXVALUE 999999999 MINVALUE 1 CYCLE CACHE 20;

-- msg_queue (발송 큐)
CREATE TABLE IF NOT EXISTS msg_queue (
    mseq INT DEFAULT nextval('msg_queue_seq'),
    msg_type CHAR(1) NOT NULL DEFAULT '1',
    send_type CHAR(1) NOT NULL DEFAULT '1',
    dkey VARCHAR(50) NOT NULL DEFAULT '0',
    dcnt INT NOT NULL DEFAULT 0,
    dstaddr VARCHAR(20) NOT NULL DEFAULT '0',
    callback VARCHAR(20),
    stat CHAR(1) NOT NULL DEFAULT '0',
    subject VARCHAR(120) DEFAULT ' ',
    text_type CHAR(1) NOT NULL DEFAULT '0',
    text VARCHAR(4000) NOT NULL DEFAULT ' ',
    text2 VARCHAR(4000),
    expiretime INT DEFAULT 86400,
    filecnt INT NOT NULL DEFAULT 0,
    fileloc1 VARCHAR(512), filesize1 INT,
    fileloc2 VARCHAR(512), filesize2 INT,
    fileloc3 VARCHAR(512), filesize3 INT,
    fileloc4 VARCHAR(512), filesize4 INT,
    fileloc5 VARCHAR(512), filesize5 INT,
    filecnt_checkup INT NOT NULL DEFAULT 0,
    insert_time TIMESTAMP,
    request_time TIMESTAMP NOT NULL,
    send_time TIMESTAMP,
    report_time TIMESTAMP,
    tcprecv_time TIMESTAMP,
    save_time TIMESTAMP,
    telecom VARCHAR(10),
    result CHAR(4),
    repcnt INT NOT NULL DEFAULT 0,
    server_id INT,
    opt_id VARCHAR(20),
    opt_cmp VARCHAR(40),
    opt_post VARCHAR(40),
    opt_name VARCHAR(40),
    ext_col0 INT,
    ext_col1 VARCHAR(64),
    ext_col2 VARCHAR(32),
    ext_col3 VARCHAR(32),
    pseq VARCHAR(10),
    sender_key VARCHAR(40),
    k_template_code VARCHAR(30),
    k_expiretime INT DEFAULT 180,
    k_next_type INT DEFAULT 0,
    k_at_send_type CHAR(1) DEFAULT '0',
    k_ad_flag CHAR(1) DEFAULT 'N',
    k_attach VARCHAR(4000),
    k_attach2 VARCHAR(4000),
    CONSTRAINT pk_msg_queue PRIMARY KEY (mseq)
);
CREATE INDEX IF NOT EXISTS idx_msg_queue_sel ON msg_queue(stat, request_time, msg_type);

-- msg_result 템플릿 (이번 달)
CREATE TABLE IF NOT EXISTS msg_result_202603 (
    mseq INT NOT NULL,
    msg_type CHAR(1) NOT NULL DEFAULT '1',
    send_type CHAR(1) NOT NULL DEFAULT '1',
    dkey VARCHAR(50) NOT NULL DEFAULT '0',
    dcnt INT NOT NULL DEFAULT 0,
    dstaddr VARCHAR(20) NOT NULL,
    callback VARCHAR(20),
    stat CHAR(1) NOT NULL DEFAULT '0',
    subject VARCHAR(120),
    text_type CHAR(1) NOT NULL DEFAULT '0',
    text VARCHAR(4000),
    text2 VARCHAR(4000),
    expiretime INT DEFAULT 86400,
    filecnt INT NOT NULL DEFAULT 0,
    fileloc1 VARCHAR(512), filesize1 INT,
    fileloc2 VARCHAR(512), filesize2 INT,
    fileloc3 VARCHAR(512), filesize3 INT,
    fileloc4 VARCHAR(512), filesize4 INT,
    fileloc5 VARCHAR(512), filesize5 INT,
    filecnt_checkup INT NOT NULL DEFAULT 0,
    insert_time TIMESTAMP,
    request_time TIMESTAMP NOT NULL,
    send_time TIMESTAMP,
    report_time TIMESTAMP,
    tcprecv_time TIMESTAMP,
    save_time TIMESTAMP,
    telecom VARCHAR(10),
    result CHAR(4),
    repcnt INT NOT NULL DEFAULT 0,
    server_id INT,
    opt_id VARCHAR(20),
    opt_cmp VARCHAR(40),
    opt_post VARCHAR(40),
    opt_name VARCHAR(40),
    ext_col0 INT,
    ext_col1 VARCHAR(64),
    ext_col2 VARCHAR(32),
    ext_col3 VARCHAR(32),
    pseq VARCHAR(10),
    sender_key VARCHAR(40),
    k_template_code VARCHAR(30),
    k_expiretime INT DEFAULT 180,
    k_next_type INT DEFAULT 0,
    k_at_send_type CHAR(1),
    k_ad_flag CHAR(1),
    k_attach VARCHAR(4000),
    k_attach2 VARCHAR(4000)
);
CREATE INDEX IF NOT EXISTS idx_msg_result_202603_1 ON msg_result_202603(mseq);
CREATE INDEX IF NOT EXISTS idx_msg_result_202603_2 ON msg_result_202603(request_time);

-- msg_queue_block (차단 목록)
CREATE TABLE IF NOT EXISTS msg_queue_block (
    dstaddr VARCHAR(20) NOT NULL,
    msg_type CHAR(1) NOT NULL,
    reg_time DATE,
    memo VARCHAR(30),
    PRIMARY KEY (dstaddr, msg_type)
);

-- ══════════════════════════════════════════════
--  기본 관리자 계정 (admin / admin1234)
--  bcrypt hash for 'admin1234'
-- ══════════════════════════════════════════════
INSERT INTO users (username, password_hash, name, role)
VALUES ('admin', '$2b$12$v7wW.Wz8SRgQ6xQh309O9uLH0HRaG0LaGQIyX9ikZnLOZrL5EJANm', '관리자', 'admin')
ON CONFLICT (username) DO NOTHING;
