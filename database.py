import os

import psycopg2

from config import DB_CONFIG


def get_connection():
    """
    Создает и возвращает новое подключение к базе данных PostgreSQL.
    """
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """
    Инициализирует базу данных: создает все необходимые таблицы.
    """

    # os.path.dirname(__file__) - получает директорию текущего файла
    # os.path.abspath(__file__) - преобразует относительный путь в абсолютный
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # os.path.join - создает полный путь к create_tables.sql
    sql_path = os.path.join(base_dir, 'create_tables.sql')

    with open(sql_path, encoding='utf-8') as file:
        sql = file.read()

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Выполняем создание таблиц, если их нет
            cur.execute(sql)
        conn.commit()


def get_or_create_user(vk_id, first_name, last_name, age, sex, city_id, city_name):
    """
    Получает существующего пользователя по vk_id или создает нового.

    Использует конструкцию INSERT ... ON CONFLICT (UPSERT):
    - Если пользователь с таким vk_id существует - обновляет его данные
    - Если не существует - создает новую запись
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (vk_id, first_name, last_name, age, sex,
                                   city_id, city_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (vk_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    age = EXCLUDED.age,
                    sex = EXCLUDED.sex,
                    city_id = EXCLUDED.city_id,
                    city_name = EXCLUDED.city_name
                RETURNING id;
                """,
                # Параметры передаются отдельно - защита от SQL-инъекций
                (vk_id, first_name, last_name, age, sex, city_id, city_name),
            )
            user_id = cur.fetchone()[0]
        conn.commit()
    return user_id


def add_favorite(user_id, favorite_vk_id, first_name, last_name):
    """
    Добавляет понравившегося пользователя в избранное.

    Использует INSERT с проверкой конфликта:
    - Если запись уже существует (тот же user_id и favorite_vk_id) - ничего не делает
    - Если записи нет - добавляет новую
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO favorites (user_id, favorite_vk_id, first_name,
                                       last_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, favorite_vk_id) DO NOTHING
                RETURNING id;
                """,
                (user_id, favorite_vk_id, first_name, last_name),
            )
            # fetchone() может вернуть None, если запись не была добавлена
            result = cur.fetchone()
        conn.commit()
    # Возвращаем True если запись добавлена
    return result is not None


def get_favorites(user_id):
    """
    Получает список избранных пользователей для указанного пользователя.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT favorite_vk_id, first_name, last_name, added_at
                FROM favorites
                WHERE user_id = %s
                ORDER BY added_at DESC;
                """,
                (user_id,),
            )
            # fetchall() возвращает ВСЕ строки результата в виде списка кортежей
            return cur.fetchall()


def add_viewed_profile(user_id, profile_vk_id, first_name, last_name):
    """
    Добавляет профиль в список просмотренных, чтобы не предлагать пользователю одни и те же профили дважды.
    Функция ничего не возвращает.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO viewed_profiles (user_id, profile_vk_id,
                                             first_name, last_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, profile_vk_id) DO NOTHING;
                """,
                (user_id, profile_vk_id, first_name, last_name),
            )
        conn.commit()


def get_viewed_vk_ids(user_id):
    """
    Получает множество VK ID профилей, которые уже просмотрел пользователь.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT profile_vk_id FROM viewed_profiles
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            # Генератор множества: для каждой строки берем первый элемент (profile_vk_id)
            # cur.fetchall() возвращает список кортежей [(1,), (2,), (3,)]
            # row[0] извлекает число из каждого кортежа
            return {row[0] for row in cur.fetchall()}