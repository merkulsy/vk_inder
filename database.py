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


# # ===================== ТЕСТИРОВАНИЕ ФУНКЦИЙ =====================
#
# def test_database_functions():
#     """
#     Тестирует все функции работы с базой данных.
#     """
#
#     print("=" * 60)
#     print("ЗАПУСК ТЕСТИРОВАНИЯ ФУНКЦИЙ БАЗЫ ДАННЫХ")
#     print("=" * 60)
#
#     print("\n1. Тестирование init_db()...")
#     try:
#         init_db()
#         print("База данных инициализирована успешно")
#     except Exception as e:
#         print(f"!!!-Ошибка инициализации БД: {e}")
#         return
#
#     print("\n2. Тестирование get_or_create_user()...")
#     test_user_data = {
#         'vk_id': 123456789,
#         'first_name': 'Тест',
#         'last_name': 'Тестов',
#         'age': 25,
#         'sex': 2,
#         'city_id': 1,
#         'city_name': 'Москва'
#     }
#
#     try:
#         user_id = get_or_create_user(**test_user_data)
#         print(f"Пользователь создан/обновлен с ID: {user_id}")
#
#         user_id_again = get_or_create_user(**test_user_data)
#         assert user_id == user_id_again, "!!!-ID пользователя должен совпадать при повторном вызове"
#         print(f"Повторный вызов вернул тот же ID: {user_id_again}")
#
#     except Exception as e:
#         print(f"!!!-Ошибка создания пользователя: {e}")
#         return
#
#     print("\n3. Тестирование add_favorite()...")
#     favorite_data = {
#         'user_id': user_id,
#         'favorite_vk_id': 987654321,
#         'first_name': 'Любимый',
#         'last_name': 'Тестов'
#     }
#
#     try:
#         added = add_favorite(**favorite_data)
#         assert added is True, "Первый раз должно добавиться"
#         print("Первое добавление в избранное успешно")
#
#         added_again = add_favorite(**favorite_data)
#         assert added_again is False, "!!!-Дубликат не должен добавляться"
#         print("Повторное добавление отклонено")
#
#         another_favorite = {
#             'user_id': user_id,
#             'favorite_vk_id': 555555555,
#             'first_name': 'Другой',
#             'last_name': 'Любимый'
#         }
#         added_another = add_favorite(**another_favorite)
#         assert added_another is True, "!!!-Другой пользователь должен добавиться"
#         print("Добавление другого пользователя успешно")
#
#     except Exception as e:
#         print(f"!!!-Ошибка добавления в избранное: {e}")
#
#     print("\n4. Тестирование get_favorites()...")
#     try:
#         favorites = get_favorites(user_id)
#         print(f"Получено избранных: {len(favorites)}")
#
#         for fav in favorites:
#             # fav должен быть кортежем из 4 элементов
#             assert len(fav) == 4, f"!!!-Кортеж должен содержать 4 элемента, получено: {len(fav)}"
#             print(f"VK ID: {fav[0]}, Имя: {fav[1]} {fav[2]}, Добавлено: {fav[3]}")
#
#         favorite_ids = [fav[0] for fav in favorites]
#         assert 987654321 in favorite_ids, "!!!-Пользователь 987654321 должен быть в избранном"
#         assert 555555555 in favorite_ids, "!!!-Пользователь 555555555 должен быть в избранном"
#         print("Все добавленные пользователи найдены в списке")
#
#     except Exception as e:
#         print(f"!!!-Ошибка получения избранных: {e}")
#
#     print("\n5. Тестирование add_viewed_profile()...")
#     viewed_profiles = [
#         (111111111, 'Первый', 'Просмотренный'),
#         (222222222, 'Второй', 'Просмотренный'),
#         (333333333, 'Третий', 'Просмотренный'),
#     ]
#
#     try:
#         for vk_id, first_name, last_name in viewed_profiles:
#             add_viewed_profile(user_id, vk_id, first_name, last_name)
#
#         add_viewed_profile(user_id, 111111111, 'Первый', 'Просмотренный')
#         print("Добавлено 3 просмотренных профиля (дубликат проигнорирован)")
#
#     except Exception as e:
#         print(f"!!!-Ошибка добавления просмотренных: {e}")
#
#     print("\n6. Тестирование get_viewed_vk_ids()...")
#     try:
#         viewed_ids = get_viewed_vk_ids(user_id)
#         print(f"Получено просмотренных ID: {len(viewed_ids)}")
#
#         assert isinstance(viewed_ids, set), "!!!-Функция должна возвращать множество"
#
#         expected_ids = {111111111, 222222222, 333333333}
#         assert expected_ids.issubset(viewed_ids), "!!!-Не все добавленные ID найдены"
#         print(f"Все добавленные ID присутствуют: {viewed_ids}")
#
#     except Exception as e:
#         print(f"!!!-Ошибка получения просмотренных ID: {e}")
#
#     print("\n" + "=" * 60)
#     print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
#     print("=" * 60)
#
#     print("\nИтого:")
#     try:
#         total_favorites = len(get_favorites(user_id))
#         total_viewed = len(get_viewed_vk_ids(user_id))
#         print(f"Всего избранных: {total_favorites}")
#         print(f"Всего просмотренных: {total_viewed}")
#         print(f"Всего записей в БД: {total_favorites + total_viewed}")
#     except Exception as e:
#         print(f"!!!-Ошибка получения статистики: {e}")
#
#     print("\nВсе тесты пройдены успешно!")
#
#
# def cleanup_test_data():
#     """
#     Очищает тестовые данные из базы данных.
#     """
#     print("\nОчистка тестовых данных...")
#     try:
#         with get_connection() as conn:
#             with conn.cursor() as cur:
#                 # Удаляем тестовых пользователей
#                 cur.execute("DELETE FROM users WHERE vk_id IN (123456789, 987654321, 555555555)")
#                 # Удаляем тестовые просмотренные профили
#                 cur.execute("DELETE FROM viewed_profiles WHERE profile_vk_id IN (111111111, 222222222, 333333333)")
#                 conn.commit()
#         print("Тестовые данные очищены")
#     except Exception as e:
#         print(f"!!!-Ошибка очистки: {e}")
#
#
# if __name__ == "__main__":
#     test_database_functions()
#     cleanup_test_data()