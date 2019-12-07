import requests
import re

from functools import lru_cache


class Dictionary:
    url = "https://dictionary.cambridge.org/zht/%E6%90%9C%E7%B4%A2/direct/?datasetsearch=english-chinese-traditional&q={}"
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:71.0) Gecko/20100101 Firefox/71.0'
    }

    category_pattern = re.compile(r"https://dictionary.cambridge.org/zht/([^/]*)/")

    @classmethod
    @lru_cache(maxsize=128)
    def fetch_page(cls, url: str) -> requests.Response:
        return requests.get(url, headers=cls.headers)

    @classmethod
    def query(cls, word: str):
        resp = cls.fetch_page(cls.url.format(word))
        
        assert len(cls.category_pattern.search(resp.url).groups()) == 1  # test
        category: str = cls.category_pattern.search(resp.url).groups()[0]

        # '%E8%A9%9E%E5%85%B8' is the urlencode of the Chinese word '詞典'
        if category == '%E8%A9%9E%E5%85%B8':
            print('詞典') #
        elif category == 'spellcheck':
            print('spellcheck') #
        else:
            raise Exception("not the expect category")  # test

        return resp

