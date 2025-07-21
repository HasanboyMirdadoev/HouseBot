import telebot
import psycopg2
import os
import dotenv
import vercel_blob
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from Core.Database import Database
from Core.HouseManager import HouseManager
from Core.UserState import UserState

class HouseBot:
    def __init__(self):
        dotenv.load_dotenv('/Users/xasanboy/MY/Bots/housebot/_env')
        self.bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
        self.db = Database(os.getenv("DATABASE_URL"))
        self.house_manager = HouseManager(self.db)
        self.user_states = UserState()
        self.admin_password = os.getenv("ADMIN_PASSWORD")
        self._register_handlers()

    def _register_handlers(self):
        bot = self.bot
        bot.message_handler(commands=['start', 'help'])(self.send_welcome)
        bot.message_handler(func=lambda m: m.text == 'Поиск дома' or m.text == 'Просмотреть все дома')(self.search_home)
        bot.message_handler(func=lambda m: m.text == 'Назад')(self.go_back_to_main_menu)
        bot.message_handler(func=lambda m: m.text == 'Поиск по местоположению')(self.search_by_location_prompt)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['action'] == 'search_home')(self.search_houses_start)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['action'] == 'search_by_location')(self.search_houses_by_location)
        bot.callback_query_handler(func=lambda call: call.data.startswith("prev_") or call.data.startswith("next_"))(self.handle_navigation)
        bot.message_handler(commands=['admin'])(self.ask_password)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['action'] == 'auth_admin')(self.handle_password_entry)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['auth'] and m.text == 'Добавить дом')(self.add_house)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['auth'] and m.text == 'Сменить пароль')(self.change_password)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['auth'] and self.user_states.get(m.chat.id)['action'] == 'change_password')(self.handle_password)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['auth'] and m.text == 'Выйти')(self.admin_logout)
        bot.message_handler(func=lambda m: m.chat.id in self.user_states.states and self.user_states.get(m.chat.id)['action'] == 'add_house' and m.text in ['Шохмансур', 'Фирдауси', 'Сомони', 'Сино'])(self.add_house_description)
        bot.message_handler(func=lambda m: m.text == 'Готово')(self.finish_image_upload)
        bot.message_handler(content_types=['photo'])(self.process_image_upload)

    def send_welcome(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(types.KeyboardButton('Поиск дома'))
        self.bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=markup)
        self.user_states.reset(message.chat.id)

    def search_home(self, message):
        self.user_states.set(message.chat.id, 'action', 'search_home')
        self.show_district_menu(message)

    def show_district_menu(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            types.KeyboardButton('Шохмансур'),
            types.KeyboardButton('Фирдауси'),
            types.KeyboardButton('Сомони'),
            types.KeyboardButton('Сино'),
            types.KeyboardButton('Поиск по местоположению'),
            types.KeyboardButton('Назад')
        )
        self.bot.send_message(message.chat.id, "Выберите район:", reply_markup=markup)

    def go_back_to_main_menu(self, message):
        if self.user_states.get(message.chat.id)['auth']:
            self.admin_menu(message)
        else:
            self.send_welcome(message)

    def search_by_location_prompt(self, message):
        self.bot.send_message(message.chat.id, "Введите местоположение для поиска:")
        self.user_states.set(message.chat.id, 'action', 'search_by_location')

    def search_houses_start(self, message):
        district = message.text
        if district == 'Назад':
            self.go_back_to_main_menu(message)
            return
        houses = self.house_manager.get_houses_by_district(district)
        self.user_states.set(message.chat.id, 'district', district)
        self.user_states.set(message.chat.id, 'house_index', 0)
        self.user_states.set(message.chat.id, 'houses', houses)
        if houses:
            self.display_house(message.chat.id, 0)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('Назад'))
            self.bot.send_message(message.chat.id, "Вы можете перейти к районам, нажав кнопку «Вернуться к районам».", reply_markup=markup)
            self.user_states.set(message.chat.id, 'action', 'houses_shown')
        else:
            self.bot.send_message(message.chat.id, "Дома не найдены в этом районе.", reply_markup=types.ReplyKeyboardRemove())
            self.show_district_menu(message)

    def search_houses_by_location(self, message):
        location_keyword = message.text
        houses = self.house_manager.get_houses_by_location(location_keyword)
        self.user_states.set(message.chat.id, 'houses', houses)
        self.user_states.set(message.chat.id, 'house_index', 0)
        if houses:
            self.display_house(message.chat.id, 0)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('Назад'))
            self.bot.send_message(message.chat.id, "Вы можете перейти к районам, нажав кнопку «Вернуться к районам».", reply_markup=markup)
            self.user_states.set(message.chat.id, 'action', 'houses_shown')
        else:
            self.bot.send_message(message.chat.id, "Дома не найдены по этому местоположению.", reply_markup=types.ReplyKeyboardRemove())
            self.show_district_menu(message)

    def display_house(self, chat_id, house_index):
        houses = self.user_states.get(chat_id)['houses']
        if not houses:
            return
        house = houses[house_index]
        media_group = [InputMediaPhoto(url) for url in house["images"]]
        if media_group:
            self.bot.send_media_group(chat_id, media_group)
        caption = f"Описание: {house['description']}\nЦена: {house['price']}\nМестоположение: {house['location']}\n"
        self.bot.send_message(
            chat_id,
            caption,
            reply_markup=self.create_navigation_buttons(house_index, len(houses))
        )

    def create_navigation_buttons(self, house_index, total_houses):
        markup = InlineKeyboardMarkup()
        if house_index > 0:
            markup.add(InlineKeyboardButton("⬅️ Предыдущий", callback_data=f"prev_{house_index-1}"))
        if house_index < total_houses - 1:
            markup.add(InlineKeyboardButton("Следующий ➡️", callback_data=f"next_{house_index+1}"))
        markup.add(InlineKeyboardButton("🔙 Назад к районам", callback_data="back_to_districts"))
        return markup

    def handle_navigation(self, call):
        action, index = call.data.split('_')
        index = int(index)
        self.user_states.set(call.message.chat.id, 'house_index', index)
        self.display_house(call.message.chat.id, index)

    def ask_password(self, message):
        self.user_states.set(message.chat.id, 'auth', False)
        self.user_states.set(message.chat.id, 'action', 'auth_admin')
        self.bot.send_message(message.chat.id, "Введите пароль:", reply_markup=types.ReplyKeyboardRemove())

    def handle_password_entry(self, message):
        if message.text == self.admin_password:
            self.user_states.set(message.chat.id, 'auth', True)
            self.admin_menu(message)
        else:
            self.bot.send_message(message.chat.id, "Неверный пароль. Попробуйте еще раз.")

    def admin_menu(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            types.KeyboardButton('Добавить дом'),
            types.KeyboardButton('Просмотреть все дома'),
            types.KeyboardButton('Сменить пароль'),
            types.KeyboardButton('Выйти')
        )
        self.bot.send_message(message.chat.id, "Добро пожаловать, админ. Выберите действие:", reply_markup=markup)
        self.user_states.set(message.chat.id, 'action', 'admin_menu')

    def add_house(self, message):
        self.user_states.set(message.chat.id, 'action', 'add_house')
        self.select_district(message)

    def select_district(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            types.KeyboardButton('Шохмансур'),
            types.KeyboardButton('Фирдауси'),
            types.KeyboardButton('Сомони'),
            types.KeyboardButton('Сино'),
            types.KeyboardButton('Назад')
        )
        self.bot.send_message(message.chat.id, "Выберите район для нового дома:", reply_markup=markup)

    def add_house_description(self, message):
        self.user_states.set(message.chat.id, 'district', message.text)
        msg = self.bot.send_message(message.chat.id, "Введите описание дома:", reply_markup=types.ReplyKeyboardRemove())
        self.bot.register_next_step_handler(msg, self.process_description)

    def process_description(self, message):
        self.user_states.set(message.chat.id, 'description', message.text)
        msg = self.bot.send_message(message.chat.id, "Введите цену:")
        self.bot.register_next_step_handler(msg, self.process_price)

    def process_price(self, message):
        self.user_states.set(message.chat.id, 'price', message.text)
        msg = self.bot.send_message(message.chat.id, "Введите местоположение:")
        self.bot.register_next_step_handler(msg, self.process_location)

    def process_location(self, message):
        state = self.user_states.get(message.chat.id)
        house_id = self.house_manager.add_house(
            state['district'], state['description'], state['price'], message.text
        )
        self.user_states.set(message.chat.id, 'house_id', house_id)
        self.bot.send_message(message.chat.id, "Отправьте изображение дома по одному. Когда закончите, нажмите кнопку 'Готово'")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Готово'))
        self.bot.send_message(message.chat.id, "Пожалуйста, отправьте изображение дома.", reply_markup=markup)

    def process_image_upload(self, message):
        if 'house_id' not in self.user_states.get(message.chat.id):
            return
        photo = message.photo[-1]
        file_id = photo.file_id
        file_info = self.bot.get_file(file_id)
        downloaded_file = self.bot.download_file(file_info.file_path)
        file_name = f"{self.user_states.get(message.chat.id)['house_id']}_{file_id}.jpg"
        blob_url = vercel_blob.put(file_name, downloaded_file, {"Content-Type": "image/jpeg"})
        self.house_manager.add_image(self.user_states.get(message.chat.id)['house_id'], blob_url['url'])
        self.bot.send_message(message.chat.id, "Изображение успешно загружено. Отправьте следующее изображение или нажмите 'Готово'.")

    def finish_image_upload(self, message):
        self.bot.send_message(message.chat.id, "Дом успешно добавлен", reply_markup=types.ReplyKeyboardRemove())
        self.user_states.set(message.chat.id, 'auth', True)
        self.admin_menu(message)

    def change_password(self, message):
        self.user_states.set(message.chat.id, 'action', 'change_password')
        self.bot.send_message(message.chat.id, "Введите новый пароль:", reply_markup=types.ReplyKeyboardRemove())

    def handle_password(self, message):
        dotenv.set_key('_env', "ADMIN_PASSWORD", message.text)
        os.environ["ADMIN_PASSWORD"] = message.text
        self.admin_password = message.text
        self.bot.send_message(message.chat.id, "Пароль успешно обновлен.")
        self.user_states.set(message.chat.id, 'action', 'admin_menu')
        self.admin_menu(message)

    def admin_logout(self, message):
        self.bot.send_message(message.chat.id, "Вы вышли из учетной записи администратора.", reply_markup=types.ReplyKeyboardRemove())
        self.send_welcome(message)

    def run(self):
        self.bot.polling()

if __name__ == "__main__":
    HouseBot().run() 