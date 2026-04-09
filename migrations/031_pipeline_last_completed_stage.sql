-- Migration 031: Add last_completed_stage to pipeline_runs for resume support
-- Enables run_pipeline() to skip already-completed stages when resuming
-- a partially-failed run via the resume_from parameter.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'pipeline_runs'
          AND column_name  = 'last_completed_stage'
    ) THEN
        ALTER TABLE public.pipeline_runs
            ADD COLUMN last_completed_stage TEXT DEFAULT NULL;

        COMMENT ON COLUMN public.pipeline_runs.last_completed_stage IS
            'Name of the last successfully completed stage (bronze, silver, gold, forecasting). '
            'Used by run_pipeline(resume_from=...) to skip already-done stages.';

        RAISE NOTICE 'Added last_completed_stage column to pipeline_runs';
    ELSE
        RAISE NOTICE 'Column last_completed_stage already exists — skipping';
    END IF;
END;
$$;

INSERT INTO public.schema_migrations (filename) VALUES ('031_pipeline_last_completed_stage.sql')
    ON CONFLICT (filename) DO NOTHING;
