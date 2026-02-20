-- SQL Server (idempotent) migration for secretary_schedule.type
-- Run once in SSMS against yujincast DB

IF COL_LENGTH('dbo.secretary_schedule', 'type') IS NULL
BEGIN
    ALTER TABLE dbo.secretary_schedule
    ADD [type] NVARCHAR(20) NULL;
END;

UPDATE dbo.secretary_schedule
SET [type] =
    CASE
        WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'TODO' THEN 'todo'
        WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'DETAIL' THEN 'detail'
        WHEN UPPER(LTRIM(RTRIM(ISNULL([description], '')))) = 'PLAN' THEN 'schedule'
        WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[todo]%' THEN 'todo'
        WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[detail]%' THEN 'detail'
        WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[plan]%' THEN 'schedule'
        WHEN LOWER(LTRIM(RTRIM(ISNULL([description], '')))) LIKE '[schedule]%' THEN 'schedule'
        ELSE 'schedule'
    END
WHERE [type] IS NULL
   OR LTRIM(RTRIM([type])) = '';

ALTER TABLE dbo.secretary_schedule
ALTER COLUMN [type] NVARCHAR(20) NOT NULL;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_secretary_schedule_type'
      AND object_id = OBJECT_ID('dbo.secretary_schedule')
)
BEGIN
    CREATE INDEX IX_secretary_schedule_type
    ON dbo.secretary_schedule([type]);
END;
