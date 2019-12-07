import requests

from functools import lru_cache


class Dictionary:
    url = "https://dictionary.cambridge.org/zht/%E6%90%9C%E7%B4%A2/direct/?datasetsearch=english-chinese-traditional&q={}"
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:71.0) Gecko/20100101 Firefox/71.0'
    }

    @classmethod
    @lru_cache(maxsize=128)
    def query_word(cls, word: str) -> requests.Response:
        return requests.get(cls.url.format(word), headers=cls.headers)

    
    

def query(word=None):
    if word is None:
        word = input("Search word: ")
    return Dictionary.query_word(word)
