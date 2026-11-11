-- Schema for the LLM ticket triage RAG project.
-- Safe to run more than once (CREATE ... IF NOT EXISTS).

CREATE EXTENSION IF NOT EXISTS vector;

-- Support tickets. generated_category / generated_priority are what the generator
-- INTENDED when it wrote the ticket. They are NOT the ground truth for accuracy:
-- accuracy is measured against eval_labels (hand-labelled by a human).
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id           SERIAL PRIMARY KEY,
    ticket_text         TEXT      NOT NULL,
    generated_category  TEXT      NOT NULL,
    generated_priority  TEXT      NOT NULL,
    created_at          TIMESTAMP NOT NULL,
    resolved_at         TIMESTAMP
);

-- Knowledge base: SOP documents split into chunks, each with an embedding.
-- vector(768) must match EMBED_DIM in .env.
CREATE TABLE IF NOT EXISTS kb_chunks (
    chunk_id     SERIAL PRIMARY KEY,
    doc_title    TEXT        NOT NULL,
    chunk_index  INT         NOT NULL,
    content      TEXT        NOT NULL,
    embedding    vector(768) NOT NULL,
    UNIQUE (doc_title, chunk_index)
);

-- AI triage results, one row per ticket.
CREATE TABLE IF NOT EXISTS ticket_triage (
    ticket_id         INT PRIMARY KEY REFERENCES tickets(ticket_id),
    category          TEXT         NOT NULL,
    priority          TEXT         NOT NULL,
    suggested_reply   TEXT         NOT NULL,
    confidence        NUMERIC(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    needs_review      BOOLEAN      NOT NULL,
    source_chunk_ids  INT[],
    model_name        TEXT         NOT NULL,
    triaged_at        TIMESTAMP    NOT NULL DEFAULT now(),
    top_similarity    NUMERIC(4,3),
    reasoning         TEXT
);

-- For databases created before these two columns existed (safe to run again).
ALTER TABLE ticket_triage ADD COLUMN IF NOT EXISTS top_similarity NUMERIC(4,3);
ALTER TABLE ticket_triage ADD COLUMN IF NOT EXISTS reasoning TEXT;

-- Hand-labelled tickets used to measure accuracy honestly.
CREATE TABLE IF NOT EXISTS eval_labels (
    ticket_id       INT PRIMARY KEY REFERENCES tickets(ticket_id),
    human_category  TEXT NOT NULL,
    human_priority  TEXT NOT NULL
);

-- v2 additions (safe to run again) ----------------------------------------------------------
ALTER TABLE ticket_triage ADD COLUMN IF NOT EXISTS review_reason  TEXT;
ALTER TABLE ticket_triage ADD COLUMN IF NOT EXISTS prompt_version TEXT DEFAULT 'v1';
ALTER TABLE eval_labels   ADD COLUMN IF NOT EXISTS eval_set TEXT NOT NULL DEFAULT 'dev';

-- Labels from a second person (to measure how often two humans agree).
CREATE TABLE IF NOT EXISTS second_labels (
    ticket_id       INT  NOT NULL REFERENCES tickets(ticket_id),
    annotator       TEXT NOT NULL,
    human_category  TEXT NOT NULL,
    human_priority  TEXT NOT NULL,
    PRIMARY KEY (ticket_id, annotator)
);
