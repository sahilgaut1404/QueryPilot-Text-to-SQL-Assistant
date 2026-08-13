import os
import time
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

username = st.secrets["MYSQL_USER"]
password = st.secrets["MYSQL_PASSWORD"]
host = st.secrets["MYSQL_HOST"]
port = st.secrets["MYSQL_PORT"]
database = st.secrets["MYSQL_DATABASE"]


@st.cache_resource
def get_engine():

    ca_cert = st.secrets["AIVEN_CA_CERT"]

    with open("/tmp/aiven_ca.pem", "w") as f:
        f.write(ca_cert)

    return create_engine(
        f"mysql+pymysql://{username}:{password}@"
        f"{host}:{port}/{database}",
        connect_args={
            "ssl": {
                "ca": "/tmp/aiven_ca.pem"
            }
        }
    )


engine = get_engine()


# ============================================================
# Valid database columns
# ============================================================

VALID_COLUMNS = {
    "order_id", "order_date", "ship_date", "ship_mode", "customer_id",
    "customer_name", "segment", "country", "city", "state", "region",
    "product_id", "category", "sub_category", "product_name", "sales",
    "quantity", "profit", "payment_mode", "returned"
}

COLUMN_GROUPS = {
    "🧾 Order": ["order_id", "order_date", "ship_date", "ship_mode", "payment_mode", "returned"],
    "👤 Customer": ["customer_id", "customer_name", "segment"],
    "📍 Location": ["country", "city", "state", "region"],
    "📦 Product": ["product_id", "category", "sub_category", "product_name"],
    "💰 Metrics": ["sales", "quantity", "profit"],
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
        "delete", "drop", "truncate", "update",
        "alter", "insert", "destroy", "remove"
    ]

    question_lower = question.lower()

    return any(word in question_lower for word in dangerous_words)


def get_invalid_schema_term(answer):

    answer_lower = answer.lower().strip()

    invalid_terms = [
        "customer_age", "customer age", "age",
        "customer_salary", "customer salary", "salary",
        "customer_email", "customer email", "email"
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
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Global styling
# ============================================================

st.markdown("""
<style>
    /* -------- App-wide -------- */
    .stApp {
        background: radial-gradient(circle at top left, #10131a 0%, #0b0d12 55%, #08090c 100%);
    }
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

    /* -------- Header -------- */
    .app-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 18px 24px;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(99,102,241,0.18), rgba(56,189,248,0.10));
        border: 1px solid rgba(148,163,184,0.15);
        margin-bottom: 22px;
    }
    .app-header .icon-badge {
        width: 46px; height: 46px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px;
        background: linear-gradient(135deg, #6366f1, #38bdf8);
        box-shadow: 0 4px 14px rgba(99,102,241,0.4);
    }
    .app-header h1 {
        font-size: 22px; margin: 0; color: #f1f5f9; font-weight: 700;
    }
    .app-header p {
        margin: 2px 0 0 0; color: #94a3b8; font-size: 13.5px;
    }

    /* -------- Sidebar -------- */
    section[data-testid="stSidebar"] {
        background: #0d0f14;
        border-right: 1px solid rgba(148,163,184,0.12);
    }
    .sidebar-card {
        background: rgba(148,163,184,0.06);
        border: 1px solid rgba(148,163,184,0.14);
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .sidebar-card h4 {
        margin: 0 0 8px 0;
        font-size: 12.5px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #38bdf8;
    }
    .col-pill {
        display: inline-block;
        background: rgba(99,102,241,0.14);
        color: #c7d2fe;
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 20px;
        padding: 2px 10px;
        margin: 3px 4px 3px 0;
        font-size: 12px;
    }

    /* -------- Chat bubbles -------- */
    [data-testid="stChatMessage"] {
        border-radius: 14px;
        padding: 4px 6px;
        margin-bottom: 6px;
    }

    /* -------- Buttons -------- */
    .stButton > button {
        border-radius: 10px;
        border: 1px solid rgba(148,163,184,0.25);
        background: rgba(148,163,184,0.08);
        color: #e2e8f0;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #38bdf8;
        color: #38bdf8;
        background: rgba(56,189,248,0.08);
    }

    /* -------- Metric-style badges -------- */
    .stat-row { display: flex; gap: 10px; margin: 10px 0 4px 0; }
    .stat-box {
        flex: 1;
        background: rgba(148,163,184,0.06);
        border: 1px solid rgba(148,163,184,0.14);
        border-radius: 10px;
        padding: 10px 12px;
        text-align: center;
    }
    .stat-box .val { font-size: 18px; font-weight: 700; color: #f1f5f9; }
    .stat-box .lbl { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: .03em; }
</style>
""", unsafe_allow_html=True)


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

st.markdown("""
<div class="app-header">
    <div class="icon-badge">🗄️</div>
    <div>
        <h1>AI Text-to-SQL</h1>
        <p>Ask questions about your sales data in plain English — I'll write and run the SQL for you.</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.markdown("### ⚙️ Workspace")

    st.markdown(
        f"""
        <div class="sidebar-card">
            <h4>Table</h4>
            <code>sales_data</code>
        </div>
        """,
        unsafe_allow_html=True
    )

    n_queries = len(st.session_state.memory.get_all()) if hasattr(st.session_state.memory, "get_all") else len(st.session_state.messages) // 2

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-box"><div class="val">{len(st.session_state.messages)//2}</div><div class="lbl">Queries</div></div>
            <div class="stat-box"><div class="val">{len(VALID_COLUMNS)}</div><div class="lbl">Columns</div></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("📋 Available columns", expanded=False):
        for group, cols in COLUMN_GROUPS.items():
            st.markdown(f"**{group}**")
            pills = "".join(f'<span class="col-pill">{c}</span>' for c in cols)
            st.markdown(pills, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 💡 Try asking")
    example_prompts = [
        "What were total sales last quarter?",
        "Top 5 products by profit",
        "Which region had the most returns?",
    ]
    for ex in example_prompts:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["_example_prompt"] = ex

    st.divider()

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.memory = ConversationMemory()
        st.session_state.pending_question = None
        st.session_state.pending_intent = None
        st.rerun()


# ============================================================
# Display conversation history
# ============================================================

if not st.session_state.messages:
    st.info("👋 Ask a question below, or try one of the suggestions in the sidebar to get started.")

for message in st.session_state.messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])


# ============================================================
# User input
# ============================================================

question = st.chat_input("Ask your database...")

if not question and st.session_state.get("_example_prompt"):
    question = st.session_state.pop("_example_prompt")


# ============================================================
# Process question
# ============================================================

if question:

    # ----------------------------------------
    # Display user question
    # ----------------------------------------

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(question)


    # ----------------------------------------
    # Security check
    # ----------------------------------------

    if is_dangerous_request(question):

        answer = "I can't execute destructive or data-modifying operations."

        st.session_state.messages.append({"role": "assistant", "content": answer})

        with st.chat_message("assistant", avatar="🤖"):
            st.error(answer, icon="🚫")

        st.stop()


    # ----------------------------------------
    # Check if this is a clarification answer
    # ----------------------------------------

    if st.session_state.pending_question:

        original_question = st.session_state.pending_question
        previous_intent = st.session_state.pending_intent

        invalid_term = get_invalid_schema_term(question)

        if invalid_term:

            answer = (
                f"'{invalid_term}' is not available in the database.\n\n"
                "Please choose a valid database attribute such as:\n\n"
                "- customer_name\n- segment\n- country\n- city\n- state\n- region"
            )

            st.session_state.messages.append({"role": "assistant", "content": answer})

            with st.chat_message("assistant", avatar="🤖"):
                st.warning(answer, icon="⚠️")

            st.stop()

        final_question = f"""
Original question:
{original_question}

User clarification:
{question}
"""

        last = st.session_state.memory.get_last()

        intent = analyze_question(final_question, previous_context=last)

        if intent.needs_clarification:

            st.session_state.pending_question = original_question
            st.session_state.pending_intent = intent

            answer = intent.clarification_question

            st.session_state.messages.append({"role": "assistant", "content": answer})

            with st.chat_message("assistant", avatar="🤖"):
                st.warning(answer, icon="❓")

            st.stop()

        st.session_state.pending_question = None
        st.session_state.pending_intent = None

    else:

        final_question = question

        last = st.session_state.memory.get_last()

        intent = analyze_question(question, previous_context=last)

        if intent.needs_clarification:

            st.session_state.pending_question = question
            st.session_state.pending_intent = intent

            answer = intent.clarification_question

            st.session_state.messages.append({"role": "assistant", "content": answer})

            with st.chat_message("assistant", avatar="🤖"):
                st.warning(answer, icon="❓")

            st.stop()


    # ========================================================
    # Run the pipeline with live status
    # ========================================================

    with st.chat_message("assistant", avatar="🤖"):

        with st.status("Working on it...", expanded=True) as status:

            # ---- Date context ----
            date_context = get_date_context()

            # ---- Generate SQL ----
            status.update(label="✍️ Writing SQL query...")
            try:
                sql = generate_sql(final_question, intent, date_context)
                sql = clean_sql(sql)
            except Exception as e:
                status.update(label="SQL generation failed", state="error")
                answer = f"SQL generation failed: {e}"
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.error(answer)
                st.stop()

            # ---- Validate SQL ----
            status.update(label="🛡️ Validating query safety...")
            try:
                valid, final_sql = validate_and_repair(sql, final_question)
                final_sql = clean_sql(final_sql)
            except Exception as e:
                status.update(label="SQL validation failed", state="error")
                answer = f"SQL validation failed: {e}"
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.error(answer)
                st.stop()

            if not valid:
                status.update(label="Query rejected", state="error")
                answer = "I couldn't generate a safe SQL query for this request."
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.error(answer)
                st.stop()

            # ---- Execute SQL ----
            status.update(label="📡 Running query against the database...")
            t0 = time.time()
            try:
                with engine.connect() as connection:
                    result = pd.read_sql(text(final_sql), connection)
            except Exception as e:
                status.update(label="Database error", state="error")
                answer = f"Database error: {e}"
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.error(answer)
                st.stop()
            elapsed = time.time() - t0

            # ---- Generate response ----
            status.update(label="🧩 Putting together your answer...")
            try:
                answer = generate_response(final_question, result.to_string(index=False))
            except Exception as e:
                answer = f"Response generation failed: {e}"

            status.update(label="Done", state="complete", expanded=False)

        # ----------------------------------------------------
        # Final answer + supporting detail, tabbed
        # ----------------------------------------------------

        st.markdown(answer)

        st.markdown(
            f"""
            <div class="stat-row">
                <div class="stat-box"><div class="val">{len(result)}</div><div class="lbl">Rows</div></div>
                <div class="stat-box"><div class="val">{len(result.columns)}</div><div class="lbl">Columns</div></div>
                <div class="stat-box"><div class="val">{elapsed:.2f}s</div><div class="lbl">Query time</div></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab_data, tab_sql, tab_intent = st.tabs(["📊 Data", "🧠 SQL", "🔎 Intent"])

        with tab_data:
            st.dataframe(result, use_container_width=True)

        with tab_sql:
            st.code(final_sql, language="sql")

        with tab_intent:
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Entity:** {intent.entity}")
                st.write(f"**Metric:** {intent.metric}")
            with c2:
                st.write(f"**Time period:** {intent.time_period}")
                st.write(f"**Ranking:** {intent.ranking}")

    # ========================================================
    # Save message + memory
    # ========================================================

    st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.memory.add(
        question=final_question,
        intent=intent,
        sql=final_sql,
        result=result.to_string(index=False)
    )
