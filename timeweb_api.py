import logging

import requests

BASE_URL = "https://api.timeweb.ru"
TIMEOUT = 15

logger = logging.getLogger(__name__)


class TimewebError(Exception):
    """Любая ошибка при работе с API."""


class AuthError(TimewebError):
    """Неверный логин, пароль, ключ или токен."""


class TimewebClient:
    def __init__(self, app_key):
        self.app_key = app_key

    def _request(self, method, path, token=None, **kwargs):
        headers = {"accept": "application/json", "x-app-key": self.app_key}
        if token:
            headers["Authorization"] = "Bearer " + token
        try:
            resp = requests.request(
                method, BASE_URL + path, headers=headers,
                timeout=TIMEOUT, **kwargs
            )
        except requests.RequestException as exc:
            logger.error("Ошибка сети: %s", exc)
            raise TimewebError("Сервер Timeweb недоступен, попробуйте позже")

        if resp.status_code in (401, 403):
            logger.error("Отказ API: %s %s", resp.status_code, resp.text[:300])
            raise AuthError("Ошибка авторизации (код %s): %s"
                            % (resp.status_code, resp.text[:300]))
        if not resp.ok:
            logger.error("API %s %s -> %s %s", method, path,
                         resp.status_code, resp.text[:200])
            raise TimewebError("Ошибка API (код %s)" % resp.status_code)
        return resp.json()

    def login(self, login, password):
        """Возвращает токен."""
        data = self._request("POST", "/v1.2/access", auth=(login, password))
        token = data.get("token")
        if not token:
            raise TimewebError("В ответе нет токена")
        return token

    def get_balance(self, login, token):
        return self._request("GET", "/v1.1/finances/accounts/" + login, token)

    def get_sites(self, login, token):
        return self._request("GET", "/v1.1/sites/" + login, token)