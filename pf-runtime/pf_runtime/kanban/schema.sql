-- Sub-phase E: Kanban persistence (Postgres).
-- Apply with psql or migration runner; KanbanStore expects these relations.

CREATE TABLE IF NOT EXISTS pf_kanban_tasks (
    id UUID PRIMARY KEY,
    profile_slug TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    status TEXT NOT NULL DEFAULT 'backlog',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pf_kanban_profile ON pf_kanban_tasks (profile_slug);

CREATE TABLE IF NOT EXISTS pf_kanban_audit (
    id BIGSERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES pf_kanban_tasks(id) ON DELETE CASCADE,
    profile_slug TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
