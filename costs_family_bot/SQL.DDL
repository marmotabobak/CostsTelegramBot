CREATE SCHEMA family_cost_bot;

CREATE TABLE family_cost_bot.costs (
	cost_id bigserial NOT NULL,
	cost_name text NULL,
	cost_amount int4 NULL,
	cost_ts timestamp NULL,
	cost_message_text text NULL,
	user_tg_id text NULL,
	CONSTRAINT costs_pkey PRIMARY KEY (cost_id)
);

CREATE TABLE family_cost_bot.messages (
	message_id bigserial NOT NULL,
	message_text text NULL,
	message_ts timestamp NULL,
	user_tg_id text NULL,
	CONSTRAINT messages_pkey PRIMARY KEY (message_id)
);