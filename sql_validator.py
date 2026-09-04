import sqlglot
from sqlglot import exp


ALLOWED_TABLES = {"sales_data"}
ALLOWED_COLUMNS = {
    "order_id",
    "order_date",
    "ship_date",
    "ship_mode",
    "customer_id",
    "customer_name",
    "segment",
    "country",
    "city",
    "state",
    "region",
    "product_id",
    "category",
    "sub_category",
    "product_name",
    "sales",
    "quantity",
    "profit",
    "payment_mode",
    "returned"
}
def validate_columns(parsed):


    aliases = set()

    for alias in parsed.find_all(exp.Alias):

        alias_name = alias.alias

        if alias_name:
            aliases.add(alias_name.lower())



    for column in parsed.find_all(exp.Column):

        column_name = column.name.lower()
        if column_name == "*":
            continue

        if column_name in ALLOWED_COLUMNS:
            continue

        # Allow SQL aliases
        if column_name in aliases:
            continue

        return False, f"Unauthorized column: {column_name}"

    return True, "Columns are valid."

def clean_sql(sql):
    sql = sql.strip()

    if sql.startswith("```sql"):
        sql = sql[len("```sql"):].strip()

    elif sql.startswith("```"):
        sql = sql[len("```"):].strip()

    if sql.endswith("```"):
        sql = sql[:-3].strip()

    return sql


def validate_sql(sql):

    sql = clean_sql(sql)

    try:

        parsed = sqlglot.parse_one(
            sql,
            dialect="mysql"
        )

    except Exception as e:

        return False, f"Invalid SQL syntax: {e}"


    if not isinstance(parsed, exp.Select):

        return False, "Only SELECT queries are allowed."

    tables = {
        table.name.lower()
        for table in parsed.find_all(exp.Table)
    }

    unauthorized_tables = tables - ALLOWED_TABLES

    if unauthorized_tables:

        return False, (
            f"Unauthorized table(s): "
            f"{', '.join(unauthorized_tables)}"
        )

    columns_valid, column_message = validate_columns(parsed)

    if not columns_valid:

        return False, column_message

    return True, "SQL is valid and safe."


