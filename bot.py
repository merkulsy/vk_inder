# Импортируем функцию randrange для создания уникального random_id при отправке сообщений
from random import randrange

import os
# Импортируем модуль signal для обработки сигналов ОС (Ctrl+C, завершение процесса)
import signal

import vk_api

# Импортируем компоненты для создания клавиатур и цветов кнопок
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# Импортируем компоненты для работы с Long Poll API
from vk_api.longpoll import VkEventType, VkLongPoll

import database as db

from vk_client import VKClient

# from secrets import group_token, access_token
# GROUP_TOKEN = group_token # Для отправки сообщений
# USER_TOKEN = access_token # Для поиска и получения данных

GROUP_TOKEN = input('Токен группы: ')
USER_TOKEN = input('Access token пользователя: ')



# Создаем экземпляр VK API для работы от имени группы
vk = vk_api.VkApi(token=GROUP_TOKEN)

# Создаем Long Poll объект для прослушивания входящих сообщений
longpoll = VkLongPoll(vk, wait=1)

# Создаем экземпляр нашего клиента VK для работы от имени пользователя
vk_user = VKClient(USER_TOKEN)

# Словарь для хранения сессий пользователей бота
# Ключ: vk_user_id (ID пользователя ВКонтакте)
# Значение: словарь с данными сессии:
#   - db_user_id: ID пользователя в нашей БД
#   - candidates: список найденных кандидатов
#   - index: текущий индекс просматриваемого кандидата
#   - current_profile: текущий просматриваемый профиль
user_sessions = {}


def get_keyboard():
    """
    Создает и возвращает клавиатуру для бота.
    one_time=False - клавиатура не скрывается после нажатия кнопки
    """

    keyboard = VkKeyboard(one_time=False)

    # Добавляем кнопки в первом ряду (ряд формируется автоматически)
    keyboard.add_button('Следующий', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('В избранное', color=VkKeyboardColor.POSITIVE)

    # Переход на новую строку (второй ряд)
    keyboard.add_line()

    # Добавляем кнопки во втором ряду
    keyboard.add_button('Избранные', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Начать', color=VkKeyboardColor.SECONDARY)

    # Возвращаем JSON-строку для передачи в VK API
    return keyboard.get_keyboard()


def write_msg(user_id, message, attachment=None):
    """
    Отправляет сообщение пользователю ВКонтакте.
    """

    # Формируем базовые параметры для отправки сообщения
    params = {
        'user_id': user_id,  # Получатель
        'message': message,  # Текст сообщения
        'random_id': randrange(10 ** 7),  # Случайный ID (защита от дублей)
        'keyboard': get_keyboard(),  # Клавиатура для управления
    }

    # Если есть вложения (фотографии), добавляем их в параметры
    if attachment:
        params['attachment'] = attachment

    # Отправляем сообщение через VK API
    vk.method('messages.send', params)


def format_profile_text(profile):
    """
    Форматирует информацию о пользователе для отображения в сообщении.
    """

    # Извлекаем VK ID пользователя
    vk_id = profile['id']

    # Формируем полное имя (с проверкой на отсутствие полей)
    name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}"

    # Получаем ссылку на профиль через статический метод
    link = VKClient.profile_link(vk_id)

    # Извлекаем город, если нет - пишем "не указан"
    city = profile.get('city', {}).get('title', 'не указан')

    # Вычисляем возраст, если нет - пишем "возраст не указан"
    age = vk_user.calc_age(profile.get('bdate', ''))
    age_text = f'{age} лет' if age else 'возраст не указан'

    # Формируем и возвращаем отформатированный текст
    return (
        f'{name}\n'
        f'Ссылка: {link}\n'
        f'Город: {city}\n'
        f'Возраст: {age_text}'
    )


def load_candidates(bot_user_id, db_user_id, user_info):
    """
    Загружает список кандидатов для пользователя.

    Процесс загрузки:
    1. Получает список уже просмотренных профилей из БД
    2. Выполняет поиск пользователей по параметрам (возраст, пол, город)
    3. Фильтрует: исключает уже просмотренных и самого пользователя
    4. Загружает до 20 кандидатов (лимит 200)
    5. Сохраняет кандидатов в сессию пользователя
    """

    # Получаем VK ID уже просмотренных профилей
    viewed = db.get_viewed_vk_ids(db_user_id)

    # Извлекаем параметры для поиска
    city_id = user_info.get('city', {}).get('id')
    age = vk_user.calc_age(user_info.get('bdate', ''))
    sex = user_info.get('sex', 0)

    offset = 0
    candidates = []

    # Загружаем кандидатов, пока не наберем 20 или не достигнем лимита
    while len(candidates) < 20 and offset < 200:
        found = vk_user.search_users(age, sex, city_id, offset=offset)

        # Если ничего не найдено - прерываем цикл
        if not found:
            break

        # Фильтруем результаты:
        # - ID не должен быть в списке просмотренных
        # - ID не должен совпадать с ID пользователя
        for profile in found:
            if profile['id'] not in viewed and profile['id'] != bot_user_id:
                candidates.append(profile)

        # Увеличиваем смещение для следующей страницы результатов
        offset += 20

    # Сохраняем кандидатов в сессию пользователя
    user_sessions[bot_user_id] = {
        'db_user_id': db_user_id,  # ID в нашей БД
        'candidates': candidates,  # Список кандидатов
        'index': 0,  # Индекс текущей анкеты
    }

    return candidates


def show_current_profile(vk_user_id):
    """
    Отображает текущую анкету пользователю.

    Процесс:
    1. Проверяет наличие сессии и кандидатов
    2. Проверяет, не закончились ли анкеты
    3. Загружает топ-3 фотографии кандидата
    4. Формирует текст и отправляет сообщение с фото
    """

    # Получаем сессию пользователя
    session = user_sessions.get(vk_user_id)

    # Если сессии нет или список кандидатов пуст
    if not session or not session['candidates']:
        write_msg(
            vk_user_id,
            'Подходящих анкет не найдено. Попробуйте позже.',
        )
        return

    # Получаем текущий индекс и проверяем, что анкеты не закончились
    index = session['index']
    if index >= len(session['candidates']):
        write_msg(
            vk_user_id,
            'Анкеты закончились. Нажмите "Начать" для нового поиска.'
        )
        return

    # Получаем профиль по текущему индексу
    profile = session['candidates'][index]

    # Получаем топ-3 фотографии профиля
    photos = vk_user.get_top_photos(profile['id'])

    # Формируем вложения для сообщения (если есть фото)
    attachment = VKClient.photo_attachments(photos)

    # Форматируем текст анкеты
    text = format_profile_text(profile)

    # Если фото нет, добавляем пояснение
    if not photos:
        text += '\n\nФотографии недоступны.'

    # Отправляем сообщение с анкетой
    write_msg(vk_user_id, text, attachment=attachment or None)

    # Добавляем профиль в список просмотренных в БД
    db.add_viewed_profile(
        session['db_user_id'],
        profile['id'],
        profile.get('first_name', ''),
        profile.get('last_name', ''),
    )

    # Сохраняем текущий профиль в сессию для "В избранное"
    session['current_profile'] = profile


def start_search(vk_user_id):
    """
    Запускает процесс поиска анкет для пользователя.

    Процесс:
    1. Получает информацию о пользователе из VK
    2. Проверяет наличие города и возраста в профиле
    3. Сохраняет пользователя в БД (или обновляет)
    4. Загружает кандидатов
    5. Показывает первую анкету
    """

    # Получаем информацию о пользователе из VK API
    user_info = vk_user.get_user_info(vk_user_id)

    # Проверяем, что данные получены
    if not user_info:
        write_msg(vk_user_id, 'Не удалось получить данные вашего профиля.')
        return

    # Проверяем наличие города и возраста
    city = user_info.get('city')
    age = vk_user.calc_age(user_info.get('bdate', ''))

    if not city or not age:
        write_msg(
            vk_user_id,
            'Укажите в профиле VK город и дату рождения, затем нажмите "Начать".',
        )
        return

    # Добавляем пользователя в БД (или обновляем существующего)
    db_user_id = db.get_or_create_user(
        vk_id=vk_user_id,
        first_name=user_info.get('first_name', ''),
        last_name=user_info.get('last_name', ''),
        age=age,
        sex=user_info.get('sex', 0),
        city_id=city.get('id'),
        city_name=city.get('title', ''),
    )

    # Загружаем кандидатов
    candidates = load_candidates(vk_user_id, db_user_id, user_info)

    # Проверяем, что кандидаты найдены
    if not candidates:
        write_msg(
            vk_user_id,
            'По вашим параметрам никого не найдено.',
        )
        return

    # Сообщаем о количестве найденных анкет и показываем первую
    write_msg(
        vk_user_id,
        f'Найдено анкет: {len(candidates)}. Смотрим первую:'
    )
    show_current_profile(vk_user_id)


def next_profile(vk_user_id):
    """
    Показывает следующую анкету из списка кандидатов.
    """

    # Получаем сессию пользователя
    session = user_sessions.get(vk_user_id)

    # Если сессии нет - напоминаем начать поиск
    if not session:
        write_msg(vk_user_id, 'Сначала нажмите "Начать".')
        return

    # Увеличиваем индекс на 1 и показываем следующую анкету
    session['index'] += 1
    show_current_profile(vk_user_id)


def add_to_favorites(vk_user_id):
    """
    Добавляет текущую анкету в избранное пользователя.
    """

    # Получаем сессию пользователя
    session = user_sessions.get(vk_user_id)

    # Проверяем, что есть сессия и текущий профиль
    if not session or 'current_profile' not in session:
        write_msg(vk_user_id, 'Сначала откройте анкету через "Начать".')
        return

    # Получаем текущий профиль
    profile = session['current_profile']

    # Добавляем в избранное в БД
    added = db.add_favorite(
        session['db_user_id'],
        profile['id'],
        profile.get('first_name', ''),
        profile.get('last_name', ''),
    )

    # Сообщаем результат
    if added:
        write_msg(vk_user_id, 'Пользователь добавлен в избранное.')
    else:
        write_msg(vk_user_id, 'Этот пользователь уже в избранном.')


def show_favorites(vk_user_id):
    """
    Показывает список избранных пользователей.

    Процесс:
        1. Если сессии нет - получает данные пользователя из VK
        2. Создает или обновляет запись пользователя в БД
        3. Получает список избранных из БД
        4. Форматирует и отправляет сообщение со списком
    """

    # Получаем сессию пользователя
    session = user_sessions.get(vk_user_id)

    # Если сессии нет - получаем данные пользователя из VK
    if not session:
        user_info = vk_user.get_user_info(vk_user_id)
        if not user_info:
            write_msg(vk_user_id, 'Сначала нажмите "Начать".')
            return

        # Создаем пользователя в БД
        db_user_id = db.get_or_create_user(
            vk_id=vk_user_id,
            first_name=user_info.get('first_name', ''),
            last_name=user_info.get('last_name', ''),
            age=vk_user.calc_age(user_info.get('bdate', '')),
            sex=user_info.get('sex', 0),
            city_id=user_info.get('city', {}).get('id'),
            city_name=user_info.get('city', {}).get('title', ''),
        )
    else:
        # Если сессия есть - берем ID из сессии
        db_user_id = session['db_user_id']

    # Получаем список избранных из БД
    favorites = db.get_favorites(db_user_id)

    # Проверяем, есть ли избранные
    if not favorites:
        write_msg(vk_user_id, 'Список избранных пуст.')
        return

    # Форматируем список избранных
    lines = ['Избранные пользователи:']
    for vk_id, first_name, last_name, _added_at in favorites:
        link = VKClient.profile_link(vk_id)
        lines.append(f'- {first_name} {last_name}: {link}')

    # Отправляем сообщение со списком
    write_msg(vk_user_id, '\n'.join(lines))


def handle_message(vk_user_id, text):
    """
    Обрабатывает входящее сообщение от пользователя.
    """

    # Приводим текст к нижнему регистру и убираем пробелы
    text = text.strip().lower()

    # Обрабатываем команду "Начать" и ее синонимы
    if text in ('начать', 'start', 'привет', 'hello'):
        start_search(vk_user_id)

    # Обрабатываем команду "Следующий" и ее синонимы
    elif text in ('следующий', 'next', 'далее'):
        next_profile(vk_user_id)

    # Обрабатываем команду "В избранное" и ее синонимы
    elif text in ('в избранное', 'избранное', 'like'):
        add_to_favorites(vk_user_id)

    # Обрабатываем команду "Избранные" и ее синонимы
    elif text in ('избранные', 'favorites', 'список'):
        show_favorites(vk_user_id)

    # Если команда не распознана - отправляем справку
    else:
        write_msg(
            vk_user_id,
            'Используйте кнопки:\n'
            '- "Начать" — поиск анкет\n'
            '- "Следующий" — следующая анкета\n'
            '- "В избранное" — сохранить текущую анкету\n'
            '- "Избранные" — показать список',
        )


def stop_bot():
    """
    Останавливает работу бота.

    Функция вызывается при получении сигналов SIGINT (Ctrl+C) или SIGTERM.
    """

    print('\nБот остановлен.')

    # Пытаемся закрыть сессию Long Poll
    try:
        longpoll.session.close()
    except Exception:
        pass  # Игнорируем ошибки при закрытии

    # Завершаем процесс с кодом 0 (успешное завершение)
    os._exit(0)


def main():
    """
    Основная функция бота.

    Процесс:
    1. Инициализирует базу данных (создает таблицы, если их нет)
    2. Настраивает обработчики сигналов для корректного завершения
    3. Запускает основной цикл обработки сообщений

    Обработка сигналов:
        - SIGINT (Ctrl+C) - обычное прерывание
        - SIGTERM - сигнал завершения от системы (например, при остановке контейнера)

    Бесконечный цикл:
        - longpoll.check() проверяет наличие новых событий
        - При появлении нового сообщения вызывает handle_message
    """

    # Инициализируем базу данных: создаем таблицы, если их нет
    db.init_db()

    # Настраиваем обработчики сигналов
    # При получении SIGINT или SIGTERM вызываем stop_bot()
    # lambda *_: stop_bot() - игнорируем аргументы, переданные сигналом
    signal.signal(signal.SIGINT, lambda *_: stop_bot())
    signal.signal(signal.SIGTERM, lambda *_: stop_bot())

    # Сообщаем о запуске
    print('Бот VKinder запущен. Ожидание сообщений...')
    print('Остановка: Ctrl+C или кнопка Stop в PyCharm')

    try:
        # Основной цикл обработки событий
        while True:
            # Проверяем наличие новых событий
            for event in longpoll.check():
                # Фильтруем события:
                # - Только новые сообщения (MESSAGE_NEW)
                # - Только сообщения, адресованные боту (to_me=True)
                if event.type != VkEventType.MESSAGE_NEW or not event.to_me:
                    continue

                # Обрабатываем сообщение
                handle_message(event.user_id, event.text)

    except KeyboardInterrupt:
        # При нажатии Ctrl+C вызываем функцию остановки
        stop_bot()


if __name__ == '__main__':
    main()