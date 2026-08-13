import os
import pandas as pd
import streamlit as st

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from clarrification import analyze_question
from sql_generator import generate_sql
from repair_loop import validate_and_repair
from date_utils import get_date_context
from response_generator import generate_response
from conversation_memory import ConversationMemory


# ============================================================
# Configuration
# ============================================================

load_dotenv()


# ============================================================
# Database
# ============================================================

import os
import tempfile

import streamlit as st
from sqlalchemy import create_engine


username = st.secrets["MYSQL_USER"]
password = st.secrets["MYSQL_PASSWORD"]
host = st.secrets["MYSQL_HOST"]
port = st.secrets["MYSQL_PORT"]
database = st.secrets["MYSQL_DATABASE"]


@st.cache_resource
def get_engine():

    ca_cert = st.secrets["AIVEN_CA_CERT"]

    ca_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".pem",
        delete=False
    )

    ca_file.write(ca_cert)
    ca_file.close()

    return create_engine(
        f"mysql+pymysql://{username}:{password}@"
        f"{host}:{port}/{database}",
        connect_args={
            "ssl": {
                "ca": ca_file.name
            }
        }
    )


engine = get_engine()

# ============================================================
# Valid database columns
# ============================================================

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


# ============================================================
# Helper functions
# ============================================================

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


# ============================================================
# Streamlit page
# ============================================================

st.set_page_config(
    page_title="AI Text-to-SQL",
    page_icon="🗄️",
    layout="wide"
)


# ============================================================
# Session memory
# ============================================================

if "memory" not in st.session_state:

    st.session_state.memory = ConversationMemory()


if "messages" not in st.session_state:

    st.session_state.messages = []


if "pending_question" not in st.session_state:

    st.session_state.pending_question = None


if "pending_intent" not in st.session_state:

    st.session_state.pending_intent = None


# ============================================================
# Header
# ============================================================

st.title("🗄️ AI Text-to-SQL")

st.write(
    "Ask questions about the sales database using natural language."
)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header("Database")

    st.write("Table: `sales_data`")

    st.write("Available columns:")

    st.code(
        """
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
"""
    )

    if st.button("Clear conversation"):

        st.session_state.messages = []
        st.session_state.memory = ConversationMemory()
        st.session_state.pending_question = None
        st.session_state.pending_intent = None

        st.rerun()


# ============================================================
# Display conversation history
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# User input
# ============================================================

question = st.chat_input(
    "Ask your database..."
)


# ============================================================
# Process question
# ============================================================

if question:

    # ----------------------------------------
    # Display user question
    # ----------------------------------------

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)


    # ----------------------------------------
    # Security check
    # ----------------------------------------

    if is_dangerous_request(question):

        answer = (
            "I can't execute destructive or "
            "data-modifying operations."
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        with st.chat_message("assistant"):
            st.error(answer)

        st.stop()


    # ----------------------------------------
    # Check if this is a clarification answer
    # ----------------------------------------

    if st.session_state.pending_question:

        original_question = (
            st.session_state.pending_question
        )

        previous_intent = (
            st.session_state.pending_intent
        )

        # ------------------------------------
        # Invalid schema clarification
        # ------------------------------------

        invalid_term = get_invalid_schema_term(
            question
        )

        if invalid_term:

            answer = (
                f"'{invalid_term}' is not available "
                "in the database.\n\n"
                "Please choose a valid database "
                "attribute such as:\n\n"
                "- customer_name\n"
                "- segment\n"
                "- country\n"
                "- city\n"
                "- state\n"
                "- region"
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            with st.chat_message("assistant"):
                st.warning(answer)

            st.stop()


        # ------------------------------------
        # Combine question + clarification
        # ------------------------------------

        final_question = f"""
Original question:
{original_question}

User clarification:
{question}
"""


        # ------------------------------------
        # Analyze again
        # ------------------------------------

        last = st.session_state.memory.get_last()

        intent = analyze_question(
            final_question,
            previous_context=last
        )


        # ------------------------------------
        # Still needs clarification
        # ------------------------------------

        if intent.needs_clarification:

            st.session_state.pending_question = (
                original_question
            )

            st.session_state.pending_intent = intent

            answer = intent.clarification_question

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            with st.chat_message("assistant"):
                st.warning(answer)

            st.stop()


        # ------------------------------------
        # Clarification resolved
        # ------------------------------------

        st.session_state.pending_question = None
        st.session_state.pending_intent = None

    else:

        # ------------------------------------
        # Normal question
        # ------------------------------------

        final_question = question

        last = st.session_state.memory.get_last()

        intent = analyze_question(
            question,
            previous_context=last
        )


        # ------------------------------------
        # Needs clarification
        # ------------------------------------

        if intent.needs_clarification:

            st.session_state.pending_question = question
            st.session_state.pending_intent = intent

            answer = intent.clarification_question

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

            with st.chat_message("assistant"):
                st.warning(answer)

            st.stop()


    # ========================================================
    # Show intent
    # ========================================================

    with st.expander("🔎 Detected Intent"):

        st.write(
            f"**Entity:** {intent.entity}"
        )

        st.write(
            f"**Metric:** {intent.metric}"
        )

        st.write(
            f"**Time period:** {intent.time_period}"
        )

        st.write(
            f"**Ranking:** {intent.ranking}"
        )


    # ========================================================
    # Date context
    # ========================================================

    date_context = get_date_context()


    # ========================================================
    # Generate SQL
    # ========================================================

    try:

        sql = generate_sql(
            final_question,
            intent,
            date_context
        )

        sql = clean_sql(sql)

    except Exception as e:

        answer = f"SQL generation failed: {e}"

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        with st.chat_message("assistant"):
            st.error(answer)

        st.stop()


    # ========================================================
    # Validate SQL
    # ========================================================

    try:

        valid, final_sql = validate_and_repair(
            sql,
            final_question
        )

        final_sql = clean_sql(final_sql)

    except Exception as e:

        answer = f"SQL validation failed: {e}"

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        with st.chat_message("assistant"):
            st.error(answer)

        st.stop()


    if not valid:

        answer = (
            "I couldn't generate a safe SQL query "
            "for this request."
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        with st.chat_message("assistant"):
            st.error(answer)

        st.stop()


    # ========================================================
    # Show SQL
    # ========================================================

    with st.expander("🧠 Generated SQL"):

        st.code(
            final_sql,
            language="sql"
        )


    # ========================================================
    # Execute SQL
    # ========================================================

    try:

        with engine.connect() as connection:

            result = pd.read_sql(
                text(final_sql),
                connection
            )

    except Exception as e:

        answer = f"Database error: {e}"

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        with st.chat_message("assistant"):
            st.error(answer)

        st.stop()


    # ========================================================
    # Display result
    # ========================================================

    st.subheader("📊 Result")

    st.dataframe(
        result,
        use_container_width=True
    )


    # ========================================================
    # Generate AI response
    # ========================================================

    try:

        answer = generate_response(
            final_question,
            result.to_string(index=False)
        )

    except Exception as e:

        answer = f"Response generation failed: {e}"


    # ========================================================
    # Display AI response
    # ========================================================

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    with st.chat_message("assistant"):

        st.markdown(answer)


    # ========================================================
    # Save conversation memory
    # ========================================================

    st.session_state.memory.add(
        question=final_question,
        intent=intent,
        sql=final_sql,
        result=result.to_string(index=False)
    )
