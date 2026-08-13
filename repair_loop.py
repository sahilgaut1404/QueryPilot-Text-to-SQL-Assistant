from sql_validator import validate_sql
from sql_repair import repair_sql


MAX_REPAIR_ATTEMPTS = 3


def validate_and_repair(sql, original_question):

    current_sql = sql

    for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):

        print(f"\nValidation attempt: {attempt}")

        valid, message = validate_sql(current_sql)

        print("Validation:", message)

        # Valid SQL

        if valid:
            return True, current_sql

        # Dangerous / non-SELECT SQL

        if message == "Only SELECT queries are allowed.":

            print("\nUnsafe SQL detected.")
            print("Repair will NOT be attempted.")

            return False, None

        # Attempt repair for other errors

        print("\nSQL needs repair.")

        repaired_sql = repair_sql(
            current_sql,
            message,
            original_question
        )

        if repaired_sql.strip() == "CANNOT_REPAIR":

            print("\nMistral cannot confidently repair this query.")

            return False, None

        current_sql = repaired_sql

        print("\nRepaired SQL:")
        print(current_sql)

    print("\nMaximum repair attempts reached.")

    return False, None

