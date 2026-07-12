-- База данных vk_inder_db для бота VKinder

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    age INTEGER,
    sex INTEGER,
    city_id INTEGER,
    city_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    favorite_vk_id BIGINT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, favorite_vk_id)
);

CREATE TABLE IF NOT EXISTS viewed_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_vk_id BIGINT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    viewed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, profile_vk_id)
);
