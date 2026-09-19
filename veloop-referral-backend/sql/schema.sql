-- VELOOP Rewards - referral schema (PostgreSQL)
-- Generated from the SQLAlchemy models. Prefer `alembic upgrade head` in real environments.

CREATE TABLE audit_logs (
	actor_user_id VARCHAR(36), 
	action VARCHAR(48) NOT NULL, 
	entity_type VARCHAR(32) NOT NULL, 
	entity_id VARCHAR(36), 
	meta TEXT, 
	ip_hash VARCHAR(64), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_audit_action_created ON audit_logs (action, created_at);
CREATE INDEX ix_audit_entity ON audit_logs (entity_type, entity_id);

CREATE TABLE devices (
	device_hash VARCHAR(64) NOT NULL, 
	first_ip_hash VARCHAR(64), 
	last_ip_hash VARCHAR(64), 
	user_agent_family VARCHAR(64), 
	token_version INTEGER NOT NULL, 
	blocked BOOLEAN NOT NULL, 
	account_count INTEGER NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_devices_device_hash ON devices (device_hash);

CREATE TABLE idempotency_records (
	scope VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	key VARCHAR(128) NOT NULL, 
	response_body TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_idempotency_request UNIQUE (scope, user_id, key)
);

CREATE TABLE milestone_configs (
	milestone INTEGER NOT NULL, 
	reward_type VARCHAR(16) NOT NULL, 
	reward_amount INTEGER NOT NULL, 
	label VARCHAR(64) NOT NULL, 
	subtitle VARCHAR(64), 
	condition_text VARCHAR(160) NOT NULL, 
	sort_order INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_milestone_reward_type UNIQUE (milestone, reward_type)
);

CREATE TABLE referral_clicks (
	referral_code VARCHAR(16) NOT NULL, 
	referrer_user_id VARCHAR(36), 
	device_hash VARCHAR(64), 
	ip_hash VARCHAR(64), 
	user_agent_family VARCHAR(64), 
	converted_referral_id VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_clicks_code_created ON referral_clicks (referral_code, created_at);

CREATE TABLE spam_referrals (
	referral_id VARCHAR(36), 
	referrer_user_id VARCHAR(36) NOT NULL, 
	referred_user_id VARCHAR(36), 
	reason VARCHAR(64) NOT NULL, 
	reason_detail TEXT, 
	risk_category VARCHAR(32) NOT NULL, 
	device_hash VARCHAR(64), 
	ip_hash VARCHAR(64), 
	risk_score INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_spam_referrer ON spam_referrals (referrer_user_id);

CREATE TABLE users (
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(20), 
	password_hash VARCHAR(255) NOT NULL, 
	referral_code VARCHAR(16) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	sve_balance INTEGER NOT NULL, 
	token_balance INTEGER NOT NULL, 
	gem_balance INTEGER NOT NULL, 
	spin_balance INTEGER NOT NULL, 
	xp INTEGER NOT NULL, 
	level INTEGER NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (phone)
);
CREATE UNIQUE INDEX ix_users_referral_code ON users (referral_code);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE ad_events (
	user_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(32) NOT NULL, 
	provider_event_id VARCHAR(128) NOT NULL, 
	ad_unit VARCHAR(64), 
	watched_seconds INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	eligible BOOLEAN NOT NULL, 
	rejection_reason VARCHAR(64), 
	device_hash VARCHAR(64), 
	ip_hash VARCHAR(64), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ad_event_provider_id UNIQUE (provider, provider_event_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_ad_events_user_eligible ON ad_events (user_id, eligible);

CREATE TABLE referrals (
	referrer_user_id VARCHAR(36) NOT NULL, 
	referred_user_id VARCHAR(36), 
	referral_code VARCHAR(16) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attribution_source VARCHAR(32) NOT NULL, 
	risk_score INTEGER NOT NULL, 
	risk_level VARCHAR(10) NOT NULL, 
	device_id VARCHAR(36), 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_referral_referred_user UNIQUE (referred_user_id), 
	FOREIGN KEY(referrer_user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(referred_user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_referrals_referrer_user_id ON referrals (referrer_user_id);
CREATE INDEX ix_referrals_referrer_status ON referrals (referrer_user_id, status);
CREATE INDEX ix_referrals_referral_code ON referrals (referral_code);
CREATE INDEX ix_referrals_status ON referrals (status);
CREATE INDEX ix_referrals_created_at ON referrals (created_at);

CREATE TABLE reward_transactions (
	user_id VARCHAR(36) NOT NULL, 
	referral_id VARCHAR(36), 
	reward_id VARCHAR(36), 
	reward_type VARCHAR(16) NOT NULL, 
	amount INTEGER NOT NULL, 
	reason VARCHAR(120) NOT NULL, 
	milestone INTEGER, 
	source VARCHAR(32) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	balance_after INTEGER NOT NULL, 
	idempotency_key VARCHAR(190) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_txn_idempotency UNIQUE (idempotency_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_txn_user_type ON reward_transactions (user_id, reward_type);
CREATE INDEX ix_txn_source ON reward_transactions (source);

CREATE TABLE user_devices (
	user_id VARCHAR(36) NOT NULL, 
	device_id VARCHAR(36) NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_device UNIQUE (user_id, device_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE
);
CREATE INDEX ix_user_devices_device ON user_devices (device_id);

CREATE TABLE referral_progress (
	referral_id VARCHAR(36) NOT NULL, 
	referred_user_id VARCHAR(36) NOT NULL, 
	eligible_ads_watched INTEGER NOT NULL, 
	last_verified_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_progress_referral UNIQUE (referral_id), 
	FOREIGN KEY(referral_id) REFERENCES referrals (id) ON DELETE CASCADE
);
CREATE INDEX ix_referral_progress_referred_user_id ON referral_progress (referred_user_id);

CREATE TABLE referral_rewards (
	referral_id VARCHAR(36) NOT NULL, 
	referrer_user_id VARCHAR(36) NOT NULL, 
	reward_type VARCHAR(16) NOT NULL, 
	reward_amount INTEGER NOT NULL, 
	milestone INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	credited_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_reward_once UNIQUE (referral_id, milestone, reward_type), 
	FOREIGN KEY(referral_id) REFERENCES referrals (id) ON DELETE CASCADE
);
CREATE INDEX ix_rewards_referrer ON referral_rewards (referrer_user_id);
