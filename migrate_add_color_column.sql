-- SQL Server (idempotent) migration for secretary_schedule.color
-- Run once in SSMS against yujincast DB

IF COL_LENGTH('dbo.secretary_schedule', 'color') IS NULL
BEGIN
    ALTER TABLE dbo.secretary_schedule
    ADD [color] NVARCHAR(20) NULL;
END;

UPDATE dbo.secretary_schedule
SET [color] = '#5A9FD4'
WHERE [color] IS NULL
   OR LTRIM(RTRIM([color])) = '';

ALTER TABLE dbo.secretary_schedule
ALTER COLUMN [color] NVARCHAR(20) NOT NULL;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_secretary_schedule_color'
      AND object_id = OBJECT_ID('dbo.secretary_schedule')
)
BEGIN
    CREATE INDEX IX_secretary_schedule_color
    ON dbo.secretary_schedule([color]);
END;
