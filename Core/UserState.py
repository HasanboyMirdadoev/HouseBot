class UserState:
    def __init__(self):
        self.states = {}

    def get(self, chat_id):
        if chat_id not in self.states:
            self.states[chat_id] = {
                'auth': False, 'action': None, 'houses': [], 'house_index': 0
            }
        return self.states[chat_id]

    def set(self, chat_id, key, value):
        self.get(chat_id)[key] = value

    def reset(self, chat_id):
        self.states[chat_id] = {
            'auth': False, 'action': None, 'houses': [], 'house_index': 0
        }