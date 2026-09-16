-- ============================================================
-- SNOWFLAKE: SECURITY & RBAC
-- ============================================================
-- Snowflake security has 4 layers:
--   1. RBAC — who can do what (roles + privileges)
--   2. Column Masking — hide PII based on role
--   3. Row Access Policies — filter rows based on role/user
--   4. Object Tagging — classify sensitive columns for governance
-- ============================================================

USE DATABASE etl_practice;
USE WAREHOUSE practice_wh;


-- ── 1. ROLE HIERARCHY ─────────────────────────────────────────
-- Snowflake built-in roles (top to bottom, most to least powerful):
--   ACCOUNTADMIN → SYSADMIN → USERADMIN → SECURITYADMIN → PUBLIC
--
-- Best practice: never use ACCOUNTADMIN for daily work.
-- Create custom roles for each team/use-case.

USE ROLE USERADMIN;

CREATE ROLE IF NOT EXISTS etl_role;       -- runs pipelines
CREATE ROLE IF NOT EXISTS analyst_role;   -- reads Silver/Gold only
CREATE ROLE IF NOT EXISTS pii_role;       -- can see unmasked PII

-- Grant roles to users
-- GRANT ROLE etl_role     TO USER juan;
-- GRANT ROLE analyst_role TO USER analyst_user;

-- Grant role to another role (role hierarchy)
GRANT ROLE analyst_role TO ROLE etl_role;  -- etl_role inherits analyst privileges

USE ROLE SYSADMIN;

-- Grant warehouse access
GRANT USAGE ON WAREHOUSE practice_wh TO ROLE etl_role;
GRANT USAGE ON WAREHOUSE practice_wh TO ROLE analyst_role;

-- Grant database/schema access
GRANT USAGE ON DATABASE etl_practice  TO ROLE analyst_role;
GRANT USAGE ON SCHEMA etl_practice.silver TO ROLE analyst_role;
GRANT SELECT ON ALL TABLES IN SCHEMA etl_practice.silver TO ROLE analyst_role;

-- Future grants: auto-grant on new tables created in this schema
GRANT SELECT ON FUTURE TABLES IN SCHEMA etl_practice.silver TO ROLE analyst_role;

-- ETL role needs more (read bronze, write silver)
GRANT USAGE  ON SCHEMA etl_practice.bronze         TO ROLE etl_role;
GRANT SELECT ON ALL TABLES IN SCHEMA etl_practice.bronze TO ROLE etl_role;
GRANT INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA etl_practice.silver     TO ROLE etl_role;


-- ── 2. COLUMN MASKING POLICY (hide PII) ──────────────────────
-- A masking policy intercepts reads on a column and returns
-- a masked value unless the caller has the right role.
-- The original data is never changed — only what you see changes.

USE SCHEMA etl_practice.silver;

-- Table with PII columns
CREATE OR REPLACE TABLE customers (
    customer_id  INT,
    name         VARCHAR(100),
    email        VARCHAR(200),   -- PII
    phone        VARCHAR(20),    -- PII
    country      VARCHAR(50)
);

INSERT INTO customers VALUES
    (1, 'Alice Smith', 'alice@example.com', '+1-555-0101', 'US'),
    (2, 'Bob Jones',   'bob@example.com',   '+44-20-7946', 'UK');

-- Create the masking policy
CREATE OR REPLACE MASKING POLICY mask_email
    AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('PII_ROLE', 'SYSADMIN', 'ACCOUNTADMIN')
            THEN val                     -- full value for privileged roles
        ELSE REGEXP_REPLACE(val, '.+@', '***@')  -- mask local part
    END;

CREATE OR REPLACE MASKING POLICY mask_phone
    AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('PII_ROLE', 'SYSADMIN', 'ACCOUNTADMIN')
            THEN val
        ELSE '***-***-****'
    END;

-- Apply policies to columns
ALTER TABLE customers MODIFY COLUMN email SET MASKING POLICY mask_email;
ALTER TABLE customers MODIFY COLUMN phone SET MASKING POLICY mask_phone;

-- Test: as analyst_role you see masked values
USE ROLE analyst_role;
SELECT * FROM etl_practice.silver.customers;
-- email → ***@example.com   phone → ***-***-****

-- As pii_role you see real values
USE ROLE SYSADMIN;
GRANT ROLE pii_role TO ROLE SYSADMIN;
USE ROLE pii_role;
SELECT * FROM etl_practice.silver.customers;
-- email → alice@example.com   phone → +1-555-0101

USE ROLE SYSADMIN;


-- ── 3. ROW ACCESS POLICY (filter rows by role/user) ───────────
-- A row access policy returns a BOOLEAN per row.
-- Rows where the policy returns FALSE are invisible to the caller.
-- Applied transparently — callers cannot tell rows are being filtered.

-- Simulate a multi-tenant orders table
CREATE OR REPLACE TABLE etl_practice.silver.tenant_orders (
    order_id   INT,
    tenant_id  INT,
    amount     NUMBER(10,2),
    status     VARCHAR(20)
);

INSERT INTO etl_practice.silver.tenant_orders VALUES
    (1, 10, 200.00, 'completed'),
    (2, 10, 150.00, 'pending'),
    (3, 20, 300.00, 'completed'),
    (4, 30,  50.00, 'cancelled');

-- Assume each user has their tenant_id stored in a mapping table
CREATE OR REPLACE TABLE etl_practice.silver.user_tenant_map (
    username  VARCHAR(100),
    tenant_id INT
);
INSERT INTO etl_practice.silver.user_tenant_map VALUES
    ('JUAN', 10),
    ('ANALYST_USER', 20);

-- Row access policy: users only see their own tenant's rows
-- SYSADMIN/ACCOUNTADMIN bypass (see all rows)
CREATE OR REPLACE ROW ACCESS POLICY tenant_row_policy
    AS (tenant_id INT) RETURNS BOOLEAN ->
    CURRENT_ROLE() IN ('SYSADMIN', 'ACCOUNTADMIN')
    OR tenant_id IN (
        SELECT tenant_id FROM etl_practice.silver.user_tenant_map
        WHERE username = CURRENT_USER()
    );

ALTER TABLE etl_practice.silver.tenant_orders
    ADD ROW ACCESS POLICY tenant_row_policy ON (tenant_id);

-- Test: SYSADMIN sees all 4 rows
SELECT COUNT(*) FROM etl_practice.silver.tenant_orders;  -- 4

-- As JUAN (tenant 10) → sees only 2 rows
-- As ANALYST_USER (tenant 20) → sees only 1 row

-- Remove policy
-- ALTER TABLE etl_practice.silver.tenant_orders
--     DROP ROW ACCESS POLICY tenant_row_policy;


-- ── 4. OBJECT TAGGING (data classification) ──────────────────
-- Tags are labels you attach to columns, tables, or schemas.
-- Used for data governance: find all PII columns across the account.

CREATE OR REPLACE TAG pii_tag
    ALLOWED_VALUES 'email', 'phone', 'ssn', 'name';

-- Tag columns
ALTER TABLE customers MODIFY COLUMN email   SET TAG pii_tag = 'email';
ALTER TABLE customers MODIFY COLUMN phone   SET TAG pii_tag = 'phone';
ALTER TABLE customers MODIFY COLUMN name    SET TAG pii_tag = 'name';

-- Query: find all tagged PII columns in the account
SELECT tag_name, tag_value,
       object_database, object_schema, object_name, column_name
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE tag_name = 'PII_TAG'
ORDER BY object_name, column_name;


-- ── 5. NETWORK POLICIES ──────────────────────────────────────
-- Restrict login to specific IP ranges (e.g., only your VPN).

CREATE OR REPLACE NETWORK POLICY office_only
    ALLOWED_IP_LIST   = ('192.168.1.0/24', '10.0.0.0/8')
    BLOCKED_IP_LIST   = ();

-- Apply to a specific user
-- ALTER USER juan SET NETWORK_POLICY = office_only;

-- Apply account-wide
-- ALTER ACCOUNT SET NETWORK_POLICY = office_only;


-- ── INTERVIEW SUMMARY ─────────────────────────────────────────
-- Q: How do you prevent analysts from seeing email addresses?
-- A: Create a MASKING POLICY that returns the masked value unless
--    CURRENT_ROLE() has the privileged role. Apply it to the column.
--    The underlying data is unchanged — only the view is masked.
--
-- Q: How do you ensure Tenant A cannot see Tenant B's data?
-- A: ROW ACCESS POLICY on the tenant_id column. The policy evaluates
--    a BOOLEAN per row at query time. Rows returning FALSE are filtered
--    invisibly — the caller gets no error, just fewer rows.
--
-- Q: What is the difference between a masking policy and a row policy?
-- A: Masking → hides column values (row still exists, column shows ***)
--    Row access → hides entire rows (row is completely invisible)
--
-- Q: What is FUTURE GRANTS?
-- A: GRANT SELECT ON FUTURE TABLES IN SCHEMA ... applies the privilege
--    automatically to every new table created in that schema.
--    Without it, you must re-grant manually after each CREATE TABLE.
