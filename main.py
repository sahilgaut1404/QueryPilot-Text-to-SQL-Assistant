import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from clarrification import analyze_question
from sql_generator import generate_sql
from repair_loop import validate_and_repair
from date_utils import get_date_context
from response_generator import generate_response
from conversation_memory import ConversationMemory


# ---------------------------------------
# Load environment variables
# ---------------------------------------

load_dotenv()


# ---------------------------------------
# MySQL connection
# ---------------------------------------

username = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
database = os.getenv("MYSQL_DATABASE")

engine = create_engine(
    f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
)


# ---------------------------------------
# Valid database columns
# ---------------------------------------

VALID_COLUMNS = {
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


# ---------------------------------------
# Clean SQL
# ---------------------------------------

def clean_sql(sql):

    sql = sql.strip()

    if sql.startswith("```sql"):
        sql = sql[len("```sql"):].strip()

    elif sql.startswith("```"):
        sql = sql[len("```"):].strip()

    if sql.endswith("```"):
        sql = sql[:-3].strip()

    return sql


# ---------------------------------------
# Dangerous request detection
# ---------------------------------------

def is_dangerous_request(question):

    dangerous_words = [
        "delete",
        "drop",
        "truncate",
        "update",
        "alter",
        "insert",
        "destroy",
        "remove"
    ]

    question_lower = question.lower()

    return any(
        word in question_lower
        for word in dangerous_words
    )


# ---------------------------------------
# Check invalid schema terms
# ---------------------------------------

def get_invalid_schema_term(answer):

    answer_lower = answer.lower().strip()

    # Known invalid attributes that users may try
    invalid_terms = [
        "customer_age",
        "customer age",
        "age",
        "customer_salary",
        "customer salary",
        "salary",
        "customer_email",
        "customer email",
        "email"
    ]

    for term in invalid_terms:

        if term in answer_lower:

            # Ignore it if it is actually a valid column
            if term not in VALID_COLUMNS:

                return term

    return None


# ---------------------------------------
# Conversation memory
# ---------------------------------------

memory = ConversationMemory()


# ---------------------------------------
# Main conversation loop
# ---------------------------------------

def main():

    while True:

        # ---------------------------------------
        # 1. Get user question
        # ---------------------------------------

        question = input("\nYou: ")

        # ---------------------------------------
        # Exit
        # ---------------------------------------

        if question.lower().strip() in [
            "exit",
            "quit",
            "bye"
        ]:

            print("\nAI: Goodbye!")
            break

        # ---------------------------------------
        # 2. Security gate
        # ---------------------------------------

        if is_dangerous_request(question):

            print(
                "\nAI: I can't execute destructive or "
                "data-modifying operations."
            )

            continue

        final_question = question

        # ---------------------------------------
        # 3. Previous conversation
        # ---------------------------------------

        last = memory.get_last()

        # ---------------------------------------
        # 4. Analyze question
        # ---------------------------------------

        intent = analyze_question(
            question,
            previous_context=last
        )

        print("\nIntent:")
        print(intent)

        # ---------------------------------------
        # 5. Clarification
        # ---------------------------------------

        while intent.needs_clarification:

            print(
                "\nAI:",
                intent.clarification_question
            )

            clarification_answer = input("\nYou: ")

            # ---------------------------------------
            # Exit during clarification
            # ---------------------------------------

            if clarification_answer.lower().strip() in [
                "exit",
                "quit",
                "bye"
            ]:

                print("\nAI: Goodbye!")
                return

            # ---------------------------------------
            # Security check clarification
            # ---------------------------------------

            if is_dangerous_request(
                clarification_answer
            ):

                print(
                    "\nAI: I can't execute destructive "
                    "or data-modifying operations."
                )

                continue

            # ---------------------------------------
            # IMPORTANT:
            # Check the clarification against
            # the database schema BEFORE sending
            # it back to the LLM.
            # ---------------------------------------

            invalid_term = get_invalid_schema_term(
                clarification_answer
            )

            if invalid_term is not None:

                print(
                    f"\nAI: '{invalid_term}' is not "
                    "available in the database."
                )

                print(
                    "\nAI: Please choose a valid "
                    "database attribute, such as:"
                )

                print(
                    "customer_name, "
                    "segment, "
                    "country, "
                    "city, "
                    "state, "
                    "region"
                )

                # Stay inside clarification loop
                continue

            # ---------------------------------------
            # Combine original question +
            # clarification
            # ---------------------------------------

            final_question = f"""
Original question:
{question}

User clarification:
{clarification_answer}
"""

            # ---------------------------------------
            # Analyze again
            # ---------------------------------------

            intent = analyze_question(
                final_question,
                previous_context=last
            )

            print("\nFinal Intent:")
            print(intent)

            # ---------------------------------------
            # DO NOT force:
            #
            # intent.needs_clarification = False
            #
            # Let the analyzer decide.
            # ---------------------------------------

            if intent.needs_clarification:

                continue

            break

        # ---------------------------------------
        # 6. Get date context
        # ---------------------------------------

        date_context = get_date_context()

        # ---------------------------------------
        # 7. Generate SQL
        # ---------------------------------------

        sql = generate_sql(
            final_question,
            intent,
            date_context
        )

        print("\nGenerated SQL:")
        print(sql)

        # ---------------------------------------
        # 8. Validate + repair
        # ---------------------------------------

        valid, final_sql = validate_and_repair(
            sql,
            final_question
        )

        if not valid:

            print(
                "\nAI: I couldn't generate "
                "a safe SQL query for this request."
            )

            continue

        # ---------------------------------------
        # 9. Clean SQL
        # ---------------------------------------

        final_sql = clean_sql(final_sql)

        print("\nFinal SQL:")
        print(final_sql)

        # ---------------------------------------
        # 10. Execute SQL
        # ---------------------------------------

        try:

            with engine.connect() as connection:

                result = pd.read_sql(
                    text(final_sql),
                    connection
                )

            print("\nResult:")
            print(
                result.to_string(index=False)
            )

        except Exception as e:

            print("\nDatabase error:")
            print(e)

            continue

        # ---------------------------------------
        # 11. Generate natural-language response
        # ---------------------------------------

        try:

            answer = generate_response(
                final_question,
                result.to_string(index=False)
            )

            print("\nAI:")
            print(answer)

        except Exception as e:

            print("\nResponse generation error:")
            print(e)

            continue

        # ---------------------------------------
        # 12. Save conversation memory
        # ---------------------------------------

        memory.add(
            question=final_question,
            intent=intent,
            sql=final_sql,
            result=result.to_string(index=False)
        )


# ---------------------------------------
# Run
# ---------------------------------------

if __name__ == "__main__":
    main()