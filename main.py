import requests
import re

from functools import lru_cache
from parsel import Selector


class Dictionary:
    """A Cambridge Dictionary crawler.

    querying a word at it, it will return the result (`dict`) extracting from The Cambridge Dictionary website (https://dictionary.cambridge.org)
    """

    _url = "https://dictionary.cambridge.org/zht/%E6%90%9C%E7%B4%A2/direct/?datasetsearch=english-chinese-traditional&q={}"
    _headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:71.0) Gecko/20100101 Firefox/71.0'
    }

    _category_pattern = re.compile(
        r"https://dictionary.cambridge.org/zht/([^/]*)/")

    @classmethod
    def _fetch_page(cls, url: str) -> requests.Response:
        return requests.get(url, headers=cls._headers)

    @classmethod
    @lru_cache(maxsize=128)
    def query(cls, word: str):
        resp = cls._fetch_page(cls._url.format(word))

        assert len(cls._category_pattern.search(resp.url).groups()) == 1  # test
        category: str = cls._category_pattern.search(resp.url).groups()[0]

        # '%E8%A9%9E%E5%85%B8' is the urlencode of the Chinese word '詞典'
        if category == '%E8%A9%9E%E5%85%B8':
            return cls._parse_dictionary_items(resp)

        elif category == 'spellcheck':
            return cls._parse_spellcheck_items(resp)

        else:
            raise Exception("not the expect category")  # test

    @classmethod
    def _parse_dictionary_items(cls, response):
        """Parse dictionary items from Cambridge Dictionary (https://dictionary.cambridge.org) 
        by using CSS selector or XPath.
        """

        selector = Selector(text=response.text)

        def parse_def_block(def_block):
            return {
                'def_h': {
                    'gram': ''.join(def_block.css('.ddef_h .gram ::text').getall()),
                    'def': ''.join(def_block.css('.ddef_h .def ::text').getall())
                },
                'def_body': {
                    'trans': def_block.css('.def-body > span.trans::text').get(),
                    'examp': [
                        {
                            'eg': ''.join(examp.css('.eg ::text').getall()),
                            'trans': examp.css('.trans::text').get(),
                        }
                        for examp in def_block.css('.def-body > div.examp')
                    ]
                }
            }

        return {
            'entry-body_el': [
                {
                    'di-title': ''.join(entry_body_el.css('.di-title *::text').getall()),
                    'posgram': entry_body_el.css('.pos-header .posgram *::text').get(),
                    'uk-pron': ''.join(entry_body_el.css('.pos-header .uk .pron ::text').getall()),
                    'us-pron': ''.join(entry_body_el.css('.pos-header .us .pron ::text').getall()),
                    'sense': [
                        {
                            'sense_h': {
                                'header': ' '.join(sense.css('.dsense_h').xpath('*[position() < 3]/text()').getall()),
                                'guide_word': ' '.join(sense.css('.dsense_h .guideword span ::text').getall()),
                            },
                            'sense-body': {
                                'def_block': [
                                    parse_def_block(def_block)
                                    for def_block in sense.css('.sense-body > .def-block')
                                ],
                                'phrase_block': [
                                    {
                                        'phrase-title': ''.join(phrase_block.css('.phrase-head .phrase-title ::text').getall()),
                                        'phrase-body': {
                                            'def_block': [
                                                parse_def_block(def_block)
                                                for def_block in phrase_block.css('.phrase-body > .def-block')
                                            ]
                                        }
                                    }
                                    for phrase_block in sense.css('.sense-body .phrase-block')
                                ],
                                'more_examp': [
                                    {
                                        'eg': ''.join(eg.css('::text').getall()),
                                    }
                                    for eg in sense.css('.sense-body .daccord ul li.eg')
                                ]

                            },
                        }
                        for sense in entry_body_el.css('.dsense')
                    ],
                    'idiom': {
                        'title': entry_body_el.css('* [class*="idiom"] ::text').get(),
                        'items': [
                            {
                                'item': ''.join(item.css('::text').getall())
                            }
                            for item in entry_body_el.css('* [class*="idiom"] .item')
                        ],
                    },
                    'phrasal_verb': {
                        'title': entry_body_el.css('* [class*="phrasal_verb"] h3 ::text').get(),
                        'items': [
                            {
                                'item': ''.join(item.css('::text').getall())
                            }
                            for item in entry_body_el.css('* [class*="phrasal_verb"] .item')
                        ],
                    }
                }
                for entry_body_el in selector.css('.entry-body .entry-body__el')
            ],
            'browse': [
                {
                    'entry': ''.join(entry.css('::text').getall())
                }
                for entry in selector.css('.dbrowse div .entry_title .results .base')
            ]
        }

    @classmethod
    def _parse_spellcheck_items(cls, response):
        selector = Selector(text=response.text)
        content_part = selector.xpath(
            "/html/body/div[2]/div/div/div[2]/div[3]/div[1]/div[1]")

        return {
            'title': ''.join(content_part.css('h1 ::text').getall()),
            'description': [
                ''.join(p.css('::text').getall())
                for p in content_part.css('* > p')
            ],
            'recommend list': [
                {
                    'word': ''.join(li.css('span ::text').getall()),
                    'link': None if response.ok else li.xpath('a/@href').get()
                }
                for li in content_part.css('* > ul > li')
            ]

        }


class SimpleTemplate:

    def __init__(self, item):
        self.item = item
        self._browse_similar_word_flag = False
    
    def _flatten_list(self, list_: list):
        for item in list_:
            if isinstance(item, list):
                yield from self._flatten_list(item)
            elif isinstance(item, dict):
                yield from self._flatten_dict(item)
            elif isinstance(item, str):
                yield item

    def _flatten_dict(self, dict_: dict):
        for key, value in dict_.items():
            if isinstance(value, list):
                yield from self._flatten_list(value)
            elif isinstance(value, dict):
                yield from self._flatten_dict(value)
            elif isinstance(value, str):
                if value == '':
                    continue
                
                if key in ('title'):
                    yield ''

                if key in ('uk-pron', 'us-pron', 'eg'):
                    yield f'{key}: {value}'
                elif key == 'def':
                    yield f'\ndefination: {value}'
                elif key == 'entry':
                    if not self._browse_similar_word_flag:
                        yield '\n瀏覽相似字詞: '
                        self._browse_similar_word_flag = True
                    
                    yield f'  {value}'
                elif key == 'link':
                    yield f'  ({value})'

                else:
                    yield value

                if key in ('us-pron'):
                    yield ''

    def render(self):
        assert isinstance(self.item, dict)
        return '\n'.join(self._flatten_dict(self.item))

if __name__ == "__main__":
    print('A Cambridge Dictionaey CLI')
    print('=' * 30)

    while True:
        try:
            word = input('query a word: ')
        except EOFError:
            print('\nquit the program ~')
            break
        print('-' * 30)
        
        item = Dictionary.query(word)
        output = SimpleTemplate(item).render()
        print(output)

        print('-' * 30)