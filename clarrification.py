from typing import List, Optional
import json
import re

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

load_dotenv()


class Intent(BaseModel):

    entity: Optional[str] = Field(
        default=None,
        description="Main entity such as customer, product, order, category, region"
    )

    metric: Optional[str] = Field(
        default=None,
        description="Metric such as sales, profit, quantity, orders"
    )

    time_period: Optional[str] = Field(
        default=None,
        description="Time period such as last month, last year, this year, 2019"
    )

    ranking: Optional[str] = Field(
        default=None,
        description="Ranking such as highest, lowest, top 5, bottom 10"
    )

    needs_clarification: bool = Field(
        description="Whether the question is ambiguous or cannot be answered from the schema"
    )

    ambiguous_terms: List[str] = Field(
        default_factory=list,
        description="Ambiguous or invalid terms"
    )

    clarification_question: str = Field(
        default="",
        description="Question to ask the user if clarification is required"
    )


model = HuggingFaceEndpoint(
    repo_id="deepseek-ai/DeepSeek-R1",
    max_new_tokens=600,
    temperature=0
)

llm = ChatHuggingFace(
    llm=model,
    temperature=0
)


def extract_json(text):

    if not text:
        raise ValueError("Model returned an empty response.")

    text = str(text).strip()

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

    text = re.sub(
        r"```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")

    if start == -1:
        raise ValueError(
            f"Model did not return JSON.\n\nModel response:\n{text[:2000]}"
        )

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):

        char = text[i]

        if escape:
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:

                    candidate = text[start:i + 1]

                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass

    raise ValueError(
        f"Could not extract valid JSON from model response.\n\n"
        f"Model response:\n{text[:2000]}"
    )


def analyze_question(question, previous_context=None):

    previous_context_text = ""

    if previous_context:
        previous_context_text = f"""
Previous conversation context:

Question:
{previous_context.get("question", "")}

Intent:
{previous_context.get("intent", "")}

SQL:
{previous_context.get("sql", "")}

Result:
{previous_context.get("result", "")}
"""

    prompt = f"""
You are an intent analyzer for a Text-to-SQL system.

The database contains ONE table:

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

{previous_context_text}

Analyze the user's question.

Extract:

1. entity
2. metric
3. time_period
4. ranking

Also determine whether clarification is required.

IMPORTANT SCHEMA RULES:

You MUST NOT invent columns.

If the user asks for a column or attribute that does NOT exist
in the valid column list, clarification is required.

Example:

User:
"Show me customers by customer_age"

customer_age does NOT exist.

Therefore:

needs_clarification = true

ambiguous_terms = ["customer_age"]

clarification_question should explain that customer_age is
not available and ask the user what valid attribute they want.

Do NOT silently replace customer_age with:

segment
region
country
customer_name

Do NOT generate a generic customer query.

Another example:

User:
"Show me customers by region"

region exists.

Therefore:

needs_clarification = false
entity = customer

Another example:

User:
"Show me the best customers"

"best" is ambiguous because it could mean:

- highest sales
- highest profit
- most orders
- highest quantity

Therefore:

needs_clarification = true

Another example:

User:
"Show me customers with the highest sales"

This is clear.

Therefore:

needs_clarification = false
entity = customer
metric = sales
ranking = highest

IMPORTANT CLARIFICATION RULE:

After a clarification question, the user may provide another
answer.

You MUST analyze that answer normally.

Do NOT assume that the clarification is automatically valid.

For example:

Original:
"Show me customers by customer_age"

AI:
"customer_age is not available. What attribute would you like?"

User:
"customer_age"

This is STILL invalid.

Therefore:

needs_clarification = true

Do NOT generate SQL.

But if the user says:

"region"

then:

needs_clarification = false
entity = customer

Conversation context can be used for follow-up questions.

Example:

Previous:
"Show me customers with the highest sales"

Current:
"What about profit?"

Interpret this as:

entity = customer
metric = profit
ranking = highest

The user's current question should be interpreted using previous
context when appropriate.

IMPORTANT:

Return ONLY ONE JSON OBJECT.

Do NOT explain your reasoning.

Do NOT return markdown.

Do NOT use ```.

Do NOT write anything before or after the JSON.

Use exactly this structure:

{{
  "entity": null,
  "metric": null,
  "time_period": null,
  "ranking": null,
  "needs_clarification": false,
  "ambiguous_terms": [],
  "clarification_question": ""
}}

User question:

{question}
"""

    response = llm.invoke(prompt)

    content = response.content

    json_data = extract_json(content)

    return Intent(**json_data)