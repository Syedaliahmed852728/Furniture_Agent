import openai
import os
import re
import json
import pandas as pd

SENSITIVE_KEYWORDS = [
    'schema', 'table', 'column', 'database', 'structure', 'ddl', 'create',
    'alter', 'drop', 'insert', 'update', 'delete', 'truncate', 'grant', 'revoke',
    'sqlite_master', 'pragma', 'table_info', 'describe', 'show tables', 
    'show columns', 'information_schema', 'sys.', 'metadata', 'system', 
    'admin', 'configuration', 'settings', 'password', 'user', 'backup', 'restore'
]

SENSITIVE_PATTERNS = [
    r'what.*table.*have',
    r'show.*table',
    r'list.*table',
    r'describe.*table',
    r'what.*column',
    r'show.*column',
    r'list.*column',
    r'database.*structure',
    r'table.*structure',
    r'what.*field',
    r'show.*field',
    r'list.*field'
]
COMPILED_SENSITIVE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]

openai.api_key = os.getenv("OPENAI_API_KEY")


def is_query_sensitive(question: str) -> bool:
    lower_question = question.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', lower_question):
            print(f"Sensitive keyword detected: '{keyword}'")
            return True
    for pattern in COMPILED_SENSITIVE_PATTERNS:
        if pattern.search(lower_question):
            print(f"Sensitive pattern detected: '{pattern.pattern}'")
            return True
    return False



def fill_hierarchy_levels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    required_cols = ["StoreName", "CompanyName", "RegionName"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    mask_company_level = df["StoreName"].isna() & df["CompanyName"].notna()
    df.loc[mask_company_level, "StoreName"] = df.loc[mask_company_level, "CompanyName"]

    mask_region_level = df["CompanyName"].isna() & df["RegionName"].notna()
    df.loc[mask_region_level, "CompanyName"] = df.loc[mask_region_level, "RegionName"]

    return df


def get_column_definitions():
    """
    Returns SQL SELECT statement snippet defining all column aliases
    based on the ConsolidateData_PBI table schema.
    Includes CASE logic for [country_name] and [Store Name] per business rules.
    """
    return """
    SELECT
        CASE 
            WHEN [STATUS] = 'W' THEN 'Written'
            WHEN [STATUS] = 'D' THEN 'Delivered'
            ELSE [STATUS] 
        END AS [Sales Type],

        [Level],

        CASE 
            WHEN [Level] = '0' THEN 'Company Level Data'
            WHEN [Level] = '1' THEN 'Store Level Data'
            WHEN [Level] = '2' THEN 'Region Level Data'
            WHEN [Level] = '3' THEN 'Region without outlet Level Data'
            WHEN [Level] = '4' THEN 'Company with Outlet Level Data'
            WHEN [Level] = '5' THEN 'Salesperson Level Data'
            WHEN [Level] = '6' THEN 'Company without Outlet Level Data'
            WHEN [Level] = '7' THEN 'All Total Level data'
            ELSE CAST([Level] AS VARCHAR)
        END AS [Data Level],

    [From Date] stays as it is
    [Month Number] comes from MONTH([From_Date])
    [Year] comes from YEAR([From_Date])
    [Day] comes from DAY([From_Date])

        CASE 
            WHEN [Profitcenter_Name] IS NULL OR LTRIM(RTRIM([Profitcenter_Name])) = '' 
                THEN [Company_Name]
            WHEN [Company_Name] IS NULL OR LTRIM(RTRIM([Company_Name])) = '' 
                THEN [Region_Name]
            ELSE ''
        END AS [country_name],

        CASE 
            WHEN [Profitcenter_Name] IS NULL OR LTRIM(RTRIM([Profitcenter_Name])) = '' 
                THEN ''
            ELSE [Profitcenter_Name]
        END AS [Store Name],

        [Company_Name] AS [Company Name],
        [Profitcenter_Name] AS [Store Name Original],
        [usr_Id] AS [Salesperson ID],
        [Name] AS [Salesperson Name],
        [Sales] AS [Sales (USD)],
        [Total Sales] AS [Total Sales (USD)],
        [cogs_sale] AS [Cost of Goods (USD)],
        [Credit App#] AS [Credit Applications Count],
        [Sales$-Fin] AS [Sales with Financing (USD)],
        [Sales$-%Fin] AS [% of Sales with Financing],
        [Avg Ticket Sale] AS [Average Ticket Sale (USD)],
        [FinAvgTickets$] AS [Average Ticket Sale (Financed, USD)],
        [NonFinAvgTickets$] AS [Average Ticket Sale (Non-Financed, USD)],
        [BEDDING SALES] AS [Bedding Sales (USD)],
        [BED%] AS [Bedding Sales (%)],
        [Bed Attach Rate] AS [Bedding Attachment Rate (%)],
        [FPP SALES] AS [Furniture Protection Plan Sales (USD)],
        [FPP%] AS [Furniture Protection Plan Sales (%)],
        [FPP Attach Rate] AS [Protection Attachment Rate (%)],
        [DELIVERY SALES] AS [Delivery Sales (USD)],
        [Del %] AS [Delivery Sales (%)],
        [Del. Attach Rate] AS [Delivery Attachment Rate (%)],
        [Gross Margin] AS [Gross Margin (%)],
        [Effective Margin] AS [Effective Margin (%)],
        [COF%] AS [Cost of Financing (%)],
        [$ Discount] AS [Total Discount Amount (USD)],
        [$ Disc. %] AS [Discount Percentage],
        [Tic Disc %] AS [Ticket Discount Percentage],
        [Drop Ship Ticket] AS [Drop Ship Ticket Count],
        [Drop Ship Ticket %] AS [Drop Ship Ticket Percentage],
        [Avg Item Count Num] AS [Average Item Count (Numeric)],
        [Avg Item Count] AS [Average Item Count],
        [UPS] AS [Traffic Count],
        [UPS Closing Rate] AS [Traffic Closing Rate (%)],
        [Sales Count] AS [Number of Sales],
        [PostiveSales] AS [Positive Sales Count],
        [Actual] AS [Actual Sales (USD)],
        [Actual_PrevYear] AS [Actual Sales Previous Year (USD)],    
        [LastYearSales] AS [Last Year Sales (USD)],
        [Total Sales PrevYear] AS [Total Sales Previous Year (USD)],
        [Avg Ticket Sale PrevYear] AS [Average Ticket Sale Previous Year (USD)],
        [UPS_PrevYear] AS [Traffic Count Previous Year],
        [Traffic Count] AS [Store Traffic Count],
        [Traffic Count PrevYear] AS [Store Traffic Count Previous Year],
        [SPGI_PrevYear] AS [Sales Per Guest Index Previous Year],
        [Sales_YOY] AS [Sales Year-over-Year Change (%)],
        [AVG_YOY] AS [Average Ticket Year-over-Year Change (%)],
        [Traffic_YOY] AS [Traffic Year-over-Year Change (%)],
        [SPG_YOY] AS [Sales Per Guest Year-over-Year Change (%)],    
        [SPGI] AS [Sales Per Guest Index],
        [Fin_Attachment] AS [Financing Attachment Rate (%)],
        [region_id] AS [Region ID],
        [deletion_rate] AS [Deletion Rate (%)],
        [store_capture_rate] AS [Store Capture Rate (%)],
        [region_name] AS [Region Name],
        [delivery%_goal] AS [Delivery Sales Goal (%)],
        [bed%_goal] AS [Bedding Sales Goal (%)],
        [fpp%_goal] AS [Protection Sales Goal (%)],
        [CreditApp#_goal] AS [Credit Application Goal],
        [COF%_goal] AS [Cost of Financing Goal (%)],
        [sales_goal] AS [Sales Goal (USD)], 
        [Apps to Traffic] AS [Applications to Traffic Ratio],
        [Traffic Close Rate] AS [Traffic Close Rate (%)],
        [EstFinanceFee] AS [Estimated Finance Fee (USD)],   
        [CreditCard] AS [Credit Card Payments (USD)],
        [Check] AS [Check Payments (USD)],
        [Cash] AS [Cash Payments (USD)],
        [Fee] AS [Fees (USD)],
        [price 2] AS [Secondary Price (USD)],
        [Total Discount Sales] AS [Total Discount on Sales (USD)],
        [FinTotalTick] AS [Total Financed Tickets],
        [TotalTicket] AS [Total Tickets],
        [FinAmount] AS [Total Financed Amount (USD)],
        [Cust_Id] AS [Customer ID],
        [TotalAmt] AS [Total Amount (USD)],
        [NoTkt] AS [No. Ticket Count],
        [DELTKT] AS [Delivery Ticket Number],
        [Bedding_Tickets] AS [Bedding Ticket Count],
        [FPP_Tickets] AS [Protection Ticket Count],
        [Delivery_Tickets] AS [Delivery Ticket Count],
        [NonFinTKTAmount] AS [Non-Financed Ticket Amount (USD)],
        [NonFinTKT] AS [Non-Financed Ticket Count],
        [Tax] AS [Tax Amount (USD)],
        [Total_Traffic] AS [Total Customer Traffic]
    FROM [dbo].[ConsolidateData_PBI]
    WHERE [From_Date] IS NOT NULL
      AND ISNULL([Sales], 0) != 0
      AND ISNULL(LTRIM(RTRIM([Company_Name])), '') NOT IN ('', 'N/A')
      AND ISNULL(LTRIM(RTRIM([Region_Name])), '') NOT IN ('', 'N/A')
    ORDER BY [Company_ID], [Profitcenter_ID], [STATUS] DESC, [Team_ID], [Level], [Name]
    """


LEVEL_PHRASE_TO_CONDITION = {
    "company level data": "[Level] = '0'",
    "store level data":   "[Level] = '1'",
    "region level data":  "[Level] = '2'",
    "region without outlet level data":  "[Level] = '3'",
    "company with outlet level data":    "[Level] = '4'",
    "salesperson level data":            "[Level] = '5'",
    "company without outlet level data": "[Level] = '6'",
    "all total level data":              "[Level] = '7'",
}

def _ensure_where_block(sql: str) -> str:
    return sql if re.search(r"\bWHERE\b", sql, re.IGNORECASE) else re.sub(r"\bFROM\b", "FROM", sql, flags=re.IGNORECASE) + " WHERE 1=1"

def _append_condition(sql: str, condition: str) -> str:
    if re.search(re.escape(condition), sql, re.IGNORECASE):
        return sql
    if re.search(r"\bWHERE\b", sql, re.IGNORECASE):
        return re.sub(r"(\bWHERE\b)", r"\1", sql, flags=re.IGNORECASE) + f" AND {condition}"
    return sql + f" WHERE {condition}"

def _ensure_not_blank(sql: str, col: str) -> str:
    cond = f"ISNULL(LTRIM(RTRIM({col})), '') NOT IN ('', 'N/A')"
    if re.search(re.escape(cond), sql, re.IGNORECASE):
        return sql
    if re.search(r"\bWHERE\b", sql, re.IGNORECASE):
        return sql + f" AND {cond}"
    else:
        return sql + f" WHERE {cond}"

def _strip_trailing_order_by(sql: str) -> tuple[str, str]:
    """Return (sql_without_order_by, order_by_clause_or_empty)"""
    m = re.search(r"\bORDER\s+BY\b[\s\S]*$", sql, re.IGNORECASE)
    if not m:
        return sql, ""
    return sql[:m.start()].rstrip(), sql[m.group(0):]

def _needs_aggregation(sql: str, entity_col: str) -> bool:
    has_entity = re.search(rf"\b{re.escape(entity_col)}\b", sql, re.IGNORECASE) is not None
    has_sum = re.search(r"\bSUM\s*\(", sql, re.IGNORECASE) is not None
    has_group = re.search(r"\bGROUP\s+BY\b", sql, re.IGNORECASE) is not None
    return has_entity and not (has_sum or has_group)

def _inject_group_by_sum_sales(sql: str, entity_col: str, out_alias: str = None) -> str:
    """
    Force the SELECT to be: SELECT [entity_col] AS [alias], SUM([Sales]) AS [Sales] ... GROUP BY [entity_col]
    Keeps FROM ... WHERE ... parts intact; overwrites ORDER BY to be SUM([Sales]) DESC if none provided.
    """
    sel_match = re.search(r"^\s*SELECT\s+(TOP\s+\d+\s+)?", sql, re.IGNORECASE)
    if not sel_match:
        return sql 

    top_clause = sel_match.group(1) or ""
    from_match = re.search(r"\bFROM\b", sql, re.IGNORECASE)
    if not from_match:
        return sql

    before_from = sql[:from_match.start()]
    after_from = sql[from_match.start():]

    alias_text = f" AS [{out_alias}]" if out_alias else ""
    new_select = f"SELECT {top_clause}{entity_col}{alias_text}, SUM([Sales]) AS [Sales] "

    after_from_no_ob, order_by = _strip_trailing_order_by(after_from)

    rebuilt = new_select + after_from_no_ob
    if re.search(r"\bGROUP\s+BY\b", rebuilt, re.IGNORECASE) is None:
        rebuilt += f" GROUP BY {entity_col}"

    if re.search(r"SUM\s*\(\s*\[?Sales\]?\s*\)\s*DESC", order_by, re.IGNORECASE):
        rebuilt += " " + order_by.strip()
    else:
        rebuilt += " ORDER BY SUM([Sales]) DESC"

    return rebuilt

def _enforce_level_and_null_rules(sql: str, question: str) -> str:
    ql = question.lower()

    sql = _ensure_not_blank(sql, "[Company_Name]")
    sql = _ensure_not_blank(sql, "[Region_Name]")

    if "store level" in ql or "store level data" in ql or re.search(r"\bstore\b", ql):
        sql = _append_condition(_ensure_where_block(sql), "[Level] = '1'")
        sql = _ensure_not_blank(sql, "[Profitcenter_Name]")

    if "company level" in ql or "company level data" in ql:
        sql = _append_condition(_ensure_where_block(sql), "[Level] = '0'")
        if "IS NULL" not in sql:
            sql = sql + " AND [Profitcenter_Name] IS NULL"

    if "region level" in ql or "region level data" in ql:
        sql = _append_condition(_ensure_where_block(sql), "[Level] = '2'")
        if "Company_Name] IS NULL" not in sql:
            sql = sql + " AND [Company_Name] IS NULL"

    for phrase, cond in LEVEL_PHRASE_TO_CONDITION.items():
        if phrase in ql and re.search(re.escape(phrase), sql, re.IGNORECASE):
            sql = re.sub(re.escape(phrase), cond, sql, flags=re.IGNORECASE)

    return sql

def _auto_aggregate_if_needed(sql: str, question: str) -> str:
    """
    If query selects a name column and [Sales] without SUM/GROUP BY, aggregate by that name.
    Prioritizes store-level, then company-level, then region-level.
    """
   
    if _needs_aggregation(sql, "[Profitcenter_Name]"):
        return _inject_group_by_sum_sales(sql, "[Profitcenter_Name]", out_alias="Store Name")
    
    if _needs_aggregation(sql, "[Company_Name]"):
        return _inject_group_by_sum_sales(sql, "[Company_Name]", out_alias="Company Name")
    
    if _needs_aggregation(sql, "[Region_Name]"):
        return _inject_group_by_sum_sales(sql, "[Region_Name]", out_alias="Region Name")
    return sql


def get_sql_and_text_response(question):
    if is_query_sensitive(question):
        return "SENSITIVE_QUERY_ERROR", "User is not allowed this.", "Access Denied"

    column_definitions = get_column_definitions()

    prompt = f"""
You are an expert in generating **valid T-SQL** queries for Microsoft SQL Server.

### IMPORTANT:
- Always use the **actual column names** from the database table `[dbo].[ConsolidateData_PBI]` when writing SQL.
- The aliases in the schema below are for **human understanding only** — do NOT use them in the SQL query body (you may use output aliases with AS).
- The schema definition below is for context only:

{column_definitions}

### LEVEL DEFINITIONS (business rules):
- Level '0' → Company Level Data (Store_Name IS NULL, Company_Name NOT NULL)
- Level '1' → Store Level Data (Store_Name NOT NULL)
- Level '2' → Region Level Data (Company_Name IS NULL, Region_Name NOT NULL)

RULES:
1. Only **SELECT** queries — no modifications.
2. Use actual column names in the SQL and enclose names in square brackets.
3. Skip null/empty/'N/A' values for all displayed columns.
4. Always filter out rows where:
   - [Company_Name] IS NULL, empty, or 'N/A'
   - OR [Region_Name] IS NULL, empty, or 'N/A'
5. If a list by entity (Store/Company/Region) is requested, aggregate numeric metrics using SUM(...) and **GROUP BY** that entity. Do **not** return duplicate rows for the same entity unless explicitly asked for detail rows.
6. Unless otherwise specified, aggregate across statuses and dates (no duplication by [STATUS], dates, tickets, etc.).
7. Default sort: [Sales] DESC unless otherwise specified.
8. Return strictly this JSON (no markdown code fences):
{{
  "SQL": "<generated SQL query using actual column names>",
  "TEXT": "<short explanation in plain English>",
  "CHART_TITLE": "<chart title>"
}}

Question: "{question}"
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response['choices'][0]['message']['content'].strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content).rstrip("`").strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", content)
        if not m:
            return "SQL_PARSE_ERROR", "Could not find JSON object in response.", "Error"
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return "SQL_PARSE_ERROR", "Could not parse LLM response as JSON.", "Error"

    sql_query = (data.get("SQL") or "").strip()
    explanation = (data.get("TEXT") or "").strip()
    chart_title = (data.get("CHART_TITLE") or "").strip()

    if not sql_query.lower().startswith("select"):
        return "NON_SELECT_QUERY_ERROR", "Only read operations are allowed.", "Invalid Operation"

    sql_query = _enforce_level_and_null_rules(sql_query, question)

    sql_query = _auto_aggregate_if_needed(sql_query, question)

    return sql_query, explanation, chart_title
