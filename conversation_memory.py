class ConversationMemory:

    def __init__(self):
        self.history = []

    def add(self, question, intent, sql=None, result=None):
        self.history.append({
            "question": question,
            "intent": intent,
            "sql": sql,
            "result": result
        })

    def get_last(self):
        if not self.history:
            return None

        return self.history[-1]

    def clear(self):
        self.history = []