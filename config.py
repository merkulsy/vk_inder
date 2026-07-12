import os

# Словарь с конфигурацией подключения к базе данных PostgreSQL.
# Значения берутся из переменных окружения, а если они не заданы, то берутся по умолчанию (для локальной разработки)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'vk_inder_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
}

# Версия API ВКонтакте, актуальная на момент написания кода
VK_VERSION = '5.199'
