from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

load_dotenv()



llm = ChatMistralAI(
    model="mistral-small-2603",
    temperature=0
)


# Repair SQL

def repair_sql(sql, error_message, original_question):

    prompt = f"""
You are a careful MySQL SQL repair system.

Original user question:
{original_question}

Generated SQL:
{sql}

Validation error:
{error_message}

Database table:
sales_data

Valid columns:

order_id
order_date
ship_date
ship_mode
customer_id
customer_name
segment
country
city
state
region
product_id
category
sub_category
product_name
sales
quantity
profit
payment_mode
returned

Your task is to repair the SQL ONLY if the correction can be
determined confidently from the database schema and the user's
original question.

STRICT RULES:

1. Never invent a column.
2. Never replace an invalid column with NULL.
3. Never replace an invalid column with a random valid column.
4. Never remove an important part of the user's request just
   to make the SQL valid.
5. Only use columns from the valid column list.
6. Only generate SELECT queries.
7. Preserve the original user intent.
8. If the query cannot be confidently repaired, return exactly:

CANNOT_REPAIR

Return ONLY the corrected SQL or CANNOT_REPAIR.
"""

    response = llm.invoke(prompt)

    return response.content.strip()


