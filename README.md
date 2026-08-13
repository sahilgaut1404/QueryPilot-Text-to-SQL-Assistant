# QueryPilot

QueryPilot is a conversational Text to SQL application that lets users ask questions about a database using normal language. The application understands the question and creates an SQL query that can be checked and repaired before it is run.

## What it does

The application takes a question from the user and follows a simple process.

1. The question is checked for unsafe requests
2. The question is understood and the intent is identified
3. If the question is unclear the application asks for clarification
4. Previous conversation can be used for follow up questions
5. SQL is created from the question
6. The SQL is cleaned and checked
7. Invalid SQL can be repaired
8. The valid query is sent to MySQL
9. The result is returned to the user
10. The result is explained in normal language

## Main features

### Natural language questions

Users do not need to write SQL themselves.

Example

```text
Show me the top 5 customers by profit
```

The application creates the required SQL query and returns the result.

### Clarification

The application can ask for more information when a question has more than one possible meaning.

Example

```text
Show me the best products
```

The application can ask whether the user means highest sales highest profit highest quantity or most orders.

### Conversation memory

The application keeps previous questions in the conversation.

For example

```text
Show me the top 5 customers by profit
```

Then

```text
What about their sales
```

The second question can use the previous question for context.

### SQL validation

Generated SQL is checked before it is sent to the database.

This prevents the application from directly running every query produced by the language model.

### SQL repair

If the generated SQL has a problem the application can try to repair it and validate the query again.

### Safe database access

Requests such as deleting or changing database records are rejected.

The application is designed mainly for reading and analysing database information.

## Architecture

```text
User
  |
  v
Streamlit
  |
  v
Question Understanding
  |
  +---- Clarification
  |
  v
Conversation and Date Context
  |
  v
Mistral
  |
  v
SQL Generation
  |
  v
SQL Cleaning
  |
  v
SQL Validation
  |
  v
SQL Repair
  |
  v
Aiven MySQL
  |
  v
Query Result
  |
  v
Response Generation
  |
  v
User
```

## Database Schema

The application uses a MySQL table called `sales_data`.

The table contains 5901 records and 20 columns.

| Column | Description |
| --- | --- |
| order_id | Order identifier |
| order_date | Date when the order was placed |
| ship_date | Date when the order was shipped |
| ship_mode | Shipping method |
| customer_id | Customer identifier |
| customer_name | Customer name |
| segment | Customer segment |
| country | Country |
| city | City |
| state | State |
| region | Sales region |
| product_id | Product identifier |
| category | Product category |
| sub_category | Product sub category |
| product_name | Product name |
| sales | Sales amount |
| quantity | Number of units sold |
| profit | Profit amount |
| payment_mode | Payment method |
| returned | Return information |

## QueryPilot Evaluation

| Metric | Result |
| --- | --- |
| SQL Accuracy | 85% |
| Clarification Improvement | +45 points |
| SQL Execution Success | 100% |
| SQL Repair Success | N/A |
| Unsafe Queries Blocked | 100% |

The application was tested using normal questions ambiguous questions follow up questions invalid database attributes and unsafe database requests.

The clarification testing showed an improvement from 40 percent without clarification to 85 percent with clarification.

SQL execution was successful for the tested queries and unsafe database operations tested during development were blocked.

## Technologies used

Python

Streamlit

Mistral

LangChain

SQLAlchemy

PyMySQL

Pandas

SQLGlot

MySQL

Aiven

GitHub

## Project structure

```text
QueryPilot
|
|-- app.py
|-- clarrification.py
|-- clean.py
|-- conversation_memory.py
|-- date_utils.py
|-- execute.py
|-- loaddata.py
|-- repair_loop.py
|-- response_generator.py
|-- sql_generator.py
|-- sql_repair.py
|-- sql_validator.py
|-- requirements.txt
|-- .gitignore
```

## Example questions

```text
What is the total sales?
```

```text
Show me the top 5 customers by profit
```

```text
Show me the best products
```

```text
Which region had the most returns?
```

```text
Show me the top customers by sales in 2019
```

```text
What about their sales?
```

## Testing

I tested the application with normal questions ambiguous questions follow up questions invalid database attributes and unsafe database requests.

The application was also tested with questions that refer to attributes which are not available in the database. In these cases the application asks the user to select a valid attribute instead of generating a query using an unavailable column.

## Deployment

The application is deployed using Streamlit Community Cloud.

The source code is stored on GitHub.

The database is hosted on Aiven.

Database credentials and API keys are kept outside the source code using environment variables and Streamlit secrets.

## Running the project

Install the required packages.

```bash
pip install -r requirements.txt
```

Create your environment file and add your database details and Mistral key.

Then run the application.

```bash
streamlit run app.py
```

## Future improvements

I would like to improve the project by supporting more complex database schemas and adding stronger SQL checking.

I also want to improve query evaluation and add better handling for questions that require multiple database operations.
