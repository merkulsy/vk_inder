import requests
from secrets import group_token

class VKGroup:
    def __init__(self, group_token, version='5.199'):
        self.token = group_token
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def get_info(self):
        # Проверям токен и возвращает информацию о группе
        url = 'https://api.vk.com/method/groups.getById'
        response = requests.get(url, params=self.params)
        return response.json()

vk_group = VKGroup(group_token)
print(vk_group.get_info())
