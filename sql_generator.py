from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

load_dotenv()


llm = ChatMistralAI(
    model="ministral-3b-2512",
    temperature=0
)



def generate_sql(question, intent, date_context):



    today = date_context["today"]
    current_year = date_context["current_year"]
    previous_year = date_context["previous_year"]

    previous_year_start = date_context["previous_year_start"]
    current_year_start = date_context["current_year_start"]

    previous_month = date_context["previous_month"]
    previous_month_year = date_context["previous_month_year"]

    # Calculate last-month boundaries
    if previous_month == 12:

        next_month = 1
        next_month_year = previous_month_year + 1

    else:

        next_month = previous_month + 1
        next_month_year = previous_month_year

    last_month_start = (
        f"{previous_month_year}-{previous_month:02d}-01"
    )

    last_month_end = (
        f"{next_month_year}-{next_month:02d}-01"
    )

  

    date_information = f"""
Today:
{today}

Current year:
{current_year}

Previous year:
{previous_year}

Previous year start:
{previous_year_start}

Current year start:
{current_year_start}

Last month start:
{last_month_start}

Last month end:
{last_month_end}
"""

    prompt = f"""
You are an expert MySQL SQL generator.

You are generating SQL for a Text-to-SQL application.

Database:
MySQL

Table:
sales_data

Columns:

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

User question:

{question}

Detected intent:

Entity: {intent.entity}
Metric: {intent.metric}
Time period: {intent.time_period}
Ranking: {intent.ranking}

Date information:

{date_information}

Generate a MySQL query that answers the user's question.

RULES:

1. Use ONLY the sales_data table.

2. Use ONLY columns listed above.

3. Use MySQL syntax.

4. If ranking is highest, use ORDER BY ... DESC.

5. If ranking is lowest, use ORDER BY ... ASC.

6. If the user asks for top customers or products,
   return the top 10 unless another number is specified.

7. Use SUM(sales) when calculating customer sales.

8. Use SUM(profit) when calculating profit.

9. Use SUM(quantity) when calculating quantity.

10. Do not generate INSERT, UPDATE, DELETE, DROP,
    ALTER or TRUNCATE.

11. Return ONLY the SQL query.

12. Each row represents a product/order line,
    not necessarily a complete order.

13. The same order_id can appear in multiple rows.

14. When counting orders, ALWAYS use:

    COUNT(DISTINCT order_id)

15. NEVER use COUNT(*) as an order count.

16. When calculating total sales per order,
    first aggregate sales by order_id.

17. When calculating average sales per order,
    first calculate total sales for each order,
    then calculate the average.

18. When calculating average profit per order,
    first calculate total profit for each order,
    then calculate the average.

19. When ranking customers by number of orders,
    use COUNT(DISTINCT order_id).

20. sales represents sales/revenue for a row.

21. profit represents profit for a row.

22. quantity represents units sold for a row.

23. "highest sales" without an entity means:
    SELECT MAX(sales).

24. "highest profit" without an entity means:
    SELECT MAX(profit).

25. "lowest sales" without an entity means:
    SELECT MIN(sales).

26. "lowest profit" without an entity means:
    SELECT MIN(profit).

27. "total sales" without an entity means:
    SELECT SUM(sales).

28. "total profit" without an entity means:
    SELECT SUM(profit).

29. "average sales" means AVG(sales), unless
    the question specifically says "per order".

30. For average sales per order, use a subquery
    that first aggregates sales by order_id.

31. For average profit per order, use a subquery
    that first aggregates profit by order_id.

DATE RULES:

32. "last year" means the previous calendar year.

33. "this year" means the current calendar year.

34. "2019" means the calendar year 2019.

35. "last 12 months" or "past 12 months"
    means a rolling 12-month period from today.

36. "last month" means the previous calendar month.

37. "this month" means the current calendar month.

38. For "last year", use the supplied date boundaries:

    order_date >= '{previous_year_start}'
    AND order_date < '{current_year_start}'

39. For "this year", use:

    order_date >= '{current_year_start}'
    AND order_date <= '{today}'

40. For "last month", use EXACTLY:

    order_date >= '{last_month_start}'
    AND order_date < '{last_month_end}'

41. For a specific calendar year such as 2019,
    use:

    order_date >= '2019-01-01'
    AND order_date < '2020-01-01'

42. Do NOT invent dates.

43. Do NOT calculate dates yourself.

44. Use the date boundaries supplied in the
    Date information section.

45. Do NOT use an old hardcoded date range.

46. Do NOT use:

    DATE_SUB(CURDATE(), INTERVAL 1 YEAR)

    for "last year".

47. "last year" is the previous calendar year,
    not the previous 365 days.

48. "last 12 months" is a rolling 12-month period.

IMPORTANT:

The Date information section contains the correct
date boundaries calculated by Python.

Trust those values.

Do not replace them with other dates.

Return ONLY the SQL query.

"""

    response = llm.invoke(prompt)

    return response.content.strip()