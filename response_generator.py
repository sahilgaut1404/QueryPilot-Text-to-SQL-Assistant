from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI

load_dotenv()

llm = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0
)


def generate_response(question, result):

    prompt = f"""
You are a helpful database assistant.

The user asked:

{question}

The database returned this result:

{result}

Answer the user's question using ONLY the provided database result.

Rules:

1. Do not invent any information.
2. Do not perform calculations that are not supported by the result.
3. Be concise and clear.
4. If the result contains a ranking, present it as a numbered list.
5. Include important numbers from the result.
6. Do not show SQL unless the user asks for SQL.
7. If the result is empty, clearly say that no matching records were found.
8. Do not assume or invent a currency symbol. Use the numeric values exactly as provided unless the user specifies a currency.
8. Do not omit rows from the database result.
9. If the result contains 10 rows, present all 10 rows.
10. Do not invent, remove, or change values from the database result.
11. Do not assume a currency symbol.
Return only the natural-language answer.
"""

    response = llm.invoke(prompt)

    return response.content.strip()