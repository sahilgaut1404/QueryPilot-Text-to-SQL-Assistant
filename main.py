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



load_dotenv()



username = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
database = os.getenv("MYSQL_DATABASE")

engine = create_engine(
    f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
)



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



def clean_sql(sql):

    sql = sql.strip()

    if sql.startswith("```sql"):
        sql = sql[len("```sql"):].strip()

    elif sql.startswith("```"):
        sql = sql[len("```"):].strip()

    if sql.endswith("```"):
        sql = sql[:-3].strip()

    return sql



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


def get_invalid_schema_term(answer):

    answer_lower = answer.lower().strip()
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

            if term not in VALID_COLUMNS:

                return term

    return None



memory = ConversationMemory()



def main():

    while True:

        question = input("\nYou: ")

    

        if question.lower().strip() in [
            "exit",
            "quit",
            "bye"
        ]:

            print("\nAI: Goodbye!")
            break


        if is_dangerous_request(question):

            print(
                "\nAI: I can't execute destructive or "
                "data-modifying operations."
            )

            continue

        final_question = question


        last = memory.get_last()


        intent = analyze_question(
            question,
            previous_context=last
        )

        print("\nIntent:")
        print(intent)



        while intent.needs_clarification:

            print(
                "\nAI:",
                intent.clarification_question
            )

            clarification_answer = input("\nYou: ")

        

            if clarification_answer.lower().strip() in [
                "exit",
                "quit",
                "bye"
            ]:

                print("\nAI: Goodbye!")
                return

    

            if is_dangerous_request(
                clarification_answer
            ):

                print(
                    "\nAI: I can't execute destructive "
                    "or data-modifying operations."
                )

                continue


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
                continue

    

            final_question = f"""
Original question:
{question}

User clarification:
{clarification_answer}
"""



            intent = analyze_question(
                final_question,
                previous_context=last
            )

            print("\nFinal Intent:")
            print(intent)


            if intent.needs_clarification:

                continue

            break


        date_context = get_date_context()



        sql = generate_sql(
            final_question,
            intent,
            date_context
        )

        print("\nGenerated SQL:")
        print(sql)


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

        final_sql = clean_sql(final_sql)

        print("\nFinal SQL:")
        print(final_sql)


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


        memory.add(
            question=final_question,
            intent=intent,
            sql=final_sql,
            result=result.to_string(index=False)
        )




if __name__ == "__main__":
    main()