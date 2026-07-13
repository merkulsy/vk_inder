import requests
from secrets import access_token, user_id

class VK:

    def __init__(self, access_token, user_id, version='5.199'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def users_info(self):
        # Получаем информацию о пользователе по его ID
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        return response.json()

vk = VK(access_token, user_id)

print(vk.users_info())
