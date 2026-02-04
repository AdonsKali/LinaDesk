class DialogueState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.messages = [
            {"role": "system", "content": "Ты — девочка Лина, способная управлять системой и использовать командную строку."}
        ]

    def add(self, role, content, **extra):
        msg = {"role": role, "content": content}
        msg.update(extra)
        self.messages.append(msg)

    def get_messages(self):
        return self.messages
    

    def cut_history(self):
        total_len = 0
        for message in self.messages:
            total_len +=len(message['content'])

            if total_len >= 4000:
                print("HISTORY THRIM")
                self.messages.pop(1)


