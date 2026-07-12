# Схема базы данных vk_inder_db

## Таблица users

Хранит пользователей бота (тех, кто пишет сообщения).

| Поле       | Тип          | Описание                    |
|------------|--------------|-----------------------------|
| id         | SERIAL       | Первичный ключ              |
| vk_id      | BIGINT       | ID пользователя ВКонтакте   |
| first_name | VARCHAR(100) | Имя                         |
| last_name  | VARCHAR(100) | Фамилия                     |
| age        | INTEGER      | Возраст                     |
| sex        | INTEGER      | Пол (1 — жен., 2 — муж.)    |
| city_id    | INTEGER      | ID города ВК                |
| city_name  | VARCHAR(100) | Название города             |
| created_at | TIMESTAMP    | Дата регистрации в боте     |

## Таблица favorites

Избранные анкеты пользователя.

| Поле           | Тип          | Описание                         |
|----------------|--------------|----------------------------------|
| id             | SERIAL       | Первичный ключ                   |
| user_id        | INTEGER      | FK → users.id                    |
| favorite_vk_id | BIGINT       | ID избранного пользователя ВК    |
| first_name     | VARCHAR(100) | Имя                              |
| last_name      | VARCHAR(100) | Фамилия                          |
| added_at       | TIMESTAMP    | Дата добавления                  |

## Таблица viewed_profiles

История просмотренных анкет (результаты поиска в БД).

| Поле          | Тип          | Описание                      |
|---------------|--------------|-------------------------------|
| id            | SERIAL       | Первичный ключ                |
| user_id       | INTEGER      | FK → users.id                 |
| profile_vk_id | BIGINT       | ID просмотренного пользователя|
| first_name    | VARCHAR(100) | Имя                           |
| last_name     | VARCHAR(100) | Фамилия                       |
| viewed_at     | TIMESTAMP    | Дата просмотра                |

## Связи

```
users (1) ──< favorites
users (1) ──< viewed_profiles
```
