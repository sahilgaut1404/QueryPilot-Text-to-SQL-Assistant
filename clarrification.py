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
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    max_new_tokens=512,
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

Analyze ONLY the user's current question.

Extract:

1. entity
2. metric
3. time_period
4. ranking

Also determine whether clarification is required.

IMPORTANT SCHEMA RULES:

You MUST NOT invent columns.

If the user asks for a column or attribute that does NOT exist
in the valid column list, set needs_clarification to true.

Example:

User:
"Show me customers by customer_age"

customer_age does NOT exist.

Return:

needs_clarification = true
ambiguous_terms = ["customer_age"]

The clarification_question should explain that customer_age is
not available and ask which valid attribute the user wants.

Do NOT silently replace customer_age with:

segment
region
country
customer_name

Do NOT generate a generic customer query.

Example:

User:
"Show me customers by region"

region exists.

Return:

needs_clarification = false
entity = "customer"

Example:

User:
"Show me the best customers"

"best" is ambiguous because it could mean:

highest sales
highest profit
most orders
highest quantity

Therefore:

needs_clarification = true

Example:

User:
"Show me customers with the highest sales"

Return:

needs_clarification = false
entity = "customer"
metric = "sales"
ranking = "highest"

IMPORTANT CLARIFICATION RULE:

After a clarification question, the user may provide another answer.

You MUST analyze the new answer normally.

Do NOT assume the clarification answer is valid.

Example:

Previous question:
"Show me customers by customer_age"

Assistant:
"customer_age is not available. What attribute would you like?"

User:
"customer_age"

customer_age is still invalid.

Return:

needs_clarification = true
ambiguous_terms = ["customer_age"]

Do NOT generate SQL.

If the user instead says:

"region"

Return:

needs_clarification = false
entity = "customer"

IMPORTANT FOLLOW-UP RULE:

Use previous conversation context when the current question
clearly refers to the previous question.

Example:

Previous:
"Show me customers with the highest sales"

Current:
"What about profit?"

Return:

entity = "customer"
metric = "profit"
ranking = "highest"
needs_clarification = false

Do not add information that is not supported by the current
question or previous context.

IMPORTANT OUTPUT RULE:

Return ONLY the final JSON object.

Do NOT provide an explanation.

Do NOT provide reasoning.

Do NOT think step by step in the response.

Do NOT use markdown.

Do NOT use code fences.

Do NOT write anything before the JSON.

Do NOT write anything after the JSON.

The response MUST start with {{ and end with }}.

Use exactly these seven fields:

{{
  "entity": null,
  "metric": null,
  "time_period": null,
  "ranking": null,
  "needs_clarification": false,
  "ambiguous_terms": [],
  "clarification_question": ""
}}

All string values must use double quotes.

ambiguous_terms must always be a JSON array.

needs_clarification must always be true or false.

Return the JSON now.

User question:

{question}
"""

    response = llm.invoke(prompt)

    content = response.content

    json_data = extract_json(content)

    return Intent(**json_data)