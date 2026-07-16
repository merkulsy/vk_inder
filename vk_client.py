from datetime import datetime # для расчета возраста пользователя

import requests

from config import VK_VERSION


class VKClient:
    """
    Клиент для работы с API ВКонтакте

    Предоставляет методы для:
    - Получения информации о пользователе
    - Поиска пользователей по параметрам
    - Получения фотографий из профиля
    - Формирования вложений для отправки в сообщениях
    """

    # Базовый URL, вызываются как https://api.vk.com/method/МЕТОД
    API_URL = 'https://api.vk.com/method'

    def __init__(self, user_token):
        """
        Инициализация клиента VK.
        user_token - Токен доступа пользователя ВКонтакте.
        """

        self.user_token = user_token
        self.params = {'access_token': user_token, 'v': VK_VERSION}

    def _request(self, method, params=None):
        """
        Внутренний метод для выполнения запросов к VK API.

        Обрабатывает:
        1. Формирование URL и параметров
        2. Отправку GET-запроса
        3. Проверку ответа на ошибки
        4. Извлечение данных из ответа
        """

        url = f'{self.API_URL}/{method}'

        # Объединяем базовые параметры (токен, версия) с параметрами метода
        all_params = {**self.params, **(params or {})}

        response = requests.get(url, params=all_params, timeout=30)

        # Преобразуем JSON-ответ в словарь Python
        data = response.json()

        # Проверяем наличие ошибки в ответе
        if 'error' in data:
            error_msg = data['error'].get('error_msg', 'VK API error')
            raise RuntimeError(error_msg)

        # Если ошибок нет, возвращаем содержимое ключа 'response' или пустой словарь
        return data.get('response', {})

    def get_user_info(self, user_id):
        """
        Получает подробную информацию о пользователе ВКонтакте.

        Использует метод VK API: users.get

        Пример возвращаемых данных:
            {
                'id': 123456789,
                'first_name': 'Иван',
                'last_name': 'Иванов',
                'bdate': '01.01.2001',
                'sex': 2,  # 1 - женский, 2 - мужской
                'city': {'id': 1, 'title': 'Москва'}
            }
        """

        # Вызываем метод users.get с параметрами
        response = self._request('users.get', {
            'user_ids': user_id,  # ID пользователя
            'fields': 'bdate,sex,city',  # Запрашиваем дополнительные поля
        })

        # Если ответ пустой - пользователь не найден
        if not response:
            return None

        # Возвращаем первый (и единственный) элемент списка, даже если запрашиваем одного пользователя
        return response[0]

    def calc_age(self, bdate):
        """
        Вычисляет возраст пользователя на основе даты рождения.

        Примеры:
            calc_age('01.01.2000') -> 26 (если текущий год 2026)
            calc_age('01.01') -> None (нет года)
            calc_age('') -> None
        """

        # Проверяем, что дата указана
        if not bdate:
            return None

        parts = bdate.split('.') # '01.02.2001' -> ['01', '02', '2001']

        # Проверяем, что есть день, месяц и год (3 части)
        if len(parts) != 3:
            return None

        try:
            # Пытаемся преобразовать год в целое число
            birth_year = int(parts[2])
        except ValueError:
            return None

        # Вычисляем возраст как разницу между текущим годом и годом рождения
        return datetime.now().year - birth_year

    def search_users(self, age, sex, city_id, offset=0, count=20):
        """
        Поиск пользователей ВКонтакте по заданным параметрам.

        Использует метод VK API: users.search

        Логика поиска:
        1. Ищем людей с возрастом +/-3 года от указанного
        2. Учитываем пол (если указан)
        3. Только с фотографиями в профиле
        4. Только из указанного города

        Пример использования:
            # Ищем женщин от 25 лет
            search_users(age=25, sex=1, city_id=1)

        Пол:
            - 1 - женщины
            - 2 - мужчины
            - 0 - любой пол
        """

        # Проверяем обязательные параметры
        if not city_id or not age:
            return []

        # Расширяем диапазон возраста на +/-3 года
        # Минимальный возраст для поиска - 14 лет
        age_from = max(14, age - 3)
        # Максимальный возраст - 100 лет
        age_to = min(100, age + 3)

        # Преобразуем пол для параметров поиска:
        # Если ищем для мужчины (sex=2) -> ищем женщин (search_sex=1)
        # Если ищем для женщины (sex=1) -> ищем мужчин (search_sex=2)
        # Если пол не указан -> ищем всех (search_sex=0)
        search_sex = 1 if sex == 2 else 2 if sex == 1 else 0

        # Формируем параметры для запроса
        params = {
            'age_from': age_from,  # Минимальный возраст
            'age_to': age_to,  # Максимальный возраст
            'city': city_id,  # Город
            'count': count,  # Количество результатов
            'offset': offset,  # Смещение для пагинации
            'fields': 'bdate,city,sex',  # Какие поля запрашиваем
            'has_photo': 1,  # Только с фото в профиле
        }

        # Добавляем пол в параметры, если он указан
        if search_sex:
            params['sex'] = search_sex

        # Выполняем запрос и извлекаем список пользователей либо пустой список, если ключа 'items' нет
        result = self._request('users.search', params)
        return result.get('items', [])

    def get_top_photos(self, owner_id, limit=3):
        """
        Получает топ фотографий пользователя по количеству лайков.

        Использует метод VK API: photos.get

        Алгоритм:
        1. Запрашиваем все фотографии из профиля пользователя
        2. Сортируем по убыванию количества лайков
        3. Возвращаем топ-N фотографий
        """

        try:
            # Пытаемся получить фотографии из альбома с фотографиями профиля
            photos = self._request('photos.get', {
                'owner_id': owner_id,  # Владелец фото
                'album_id': 'profile',  # Альбом с фото профиля
                'extended': 1,  # Получить дополнительные поля (лайки, комментарии)
                'photo_sizes': 1,  # Получить размеры фотографий
            })
        except RuntimeError:
            # Если произошла ошибка (например, закрытый профиль) - возвращаем пустой список
            return []

        # Проверяем, что ответ не пустой
        if not photos:
            return []

        # Нормализуем структуру ответа (ответ может словарём или списком)
        if isinstance(photos, dict):
            items = photos.get('items', [])
        else:
            items = photos

        # Сортируем фотографии по убыванию количества лайков
        sorted_photos = sorted(
            items,
            key=lambda photo: photo.get('likes', {}).get('count', 0),
            reverse=True,
        )

        # Возвращаем первые limit фотографий
        return sorted_photos[:limit]

    @staticmethod
    def profile_link(vk_id):
        """
        Статический метод, формирующий ссылку на профиль ВКонтакте.
        """

        return f'https://vk.com/id{vk_id}'

    @staticmethod
    def photo_attachments(photos):
        """
        Статический метод, преобразующий фото в формат вложений для VK, для отправки в сообщениях через API.
        Формат вложения: 'photo{owner_id}_{photo_id}'
        При отправке сообщения через VK API:
            messages.send(..., attachment=photo_attachments(photos))
        """

        attachments = []

        # Проходим по каждой фотографии
        for photo in photos:
            # Извлекаем ID владельца и ID фотографии
            owner_id = photo.get('owner_id')
            photo_id = photo.get('id')

            # Если оба ID присутствуют - формируем вложение
            if owner_id and photo_id:
                # Формат: photo{owner_id}_{photo_id}
                attachments.append(f'photo{owner_id}_{photo_id}')

        # Соединяем все вложения через запятую
        return ','.join(attachments)


# # ===================== ТЕСТИРОВАНИЕ КЛАССА =====================
#
# # 1. ПРОСТАЯ ПРОВЕРКА (без токена)
# print("ПРОСТАЯ ПРОВЕРКА (без API)")
# print("=" * 30)
#
# client = VKClient("fake_token")
#
# print("1. profile_link(123):", client.profile_link(123))
# print("2. calc_age('01.02.2000'):", client.calc_age('01.02.2000'))
# print("3. calc_age(''):", client.calc_age(''))
# print("4. calc_age('01.02'):", client.calc_age('01.02'))
#
# photos = [{'owner_id': 1, 'id': 2}, {'owner_id': 3, 'id': 4}]
# print("5. photo_attachments:", client.photo_attachments(photos))
#
# print("=" * 30)
# print("Простая проверка пройдена!")
# print("\n")
#
#
# # 2. ПРОВЕРКА С ТОКЕНОМ
# print("ПРОВЕРКА С ТОКЕНОМ")
# print("=" * 30)
#
# from secrets import access_token, user_id
# TOKEN = access_token
# USER_ID = user_id
#
# client = VKClient(TOKEN)
#
# print("\n1. Информация о пользователе:")
# user = client.get_user_info(USER_ID)
# if user:
#     print(f"{user['first_name']} {user['last_name']}")
#     print(f"ID: {user['id']}")
#
# print("\n2. Поиск пользователей:")
# users = client.search_users(age=25, sex=2, city_id=1, count=3)
# print(f"Найдено: {len(users)}")
# for u in users[:3]:
#     print(f" - {u['first_name']} {u['last_name']}")
#
# print("\n3. Топ фото:")
# photos = client.get_top_photos(USER_ID, limit=3)
# print(f"Фото: {len(photos)}")
# for p in photos[:3]:
#     print(f" - Лайков: {p.get('likes', {}).get('count', 0)}")
#
# print("\n" + "=" * 30)
# print("ВСЕ ПРОВЕРКИ ЗАВЕРШЕНЫ!")