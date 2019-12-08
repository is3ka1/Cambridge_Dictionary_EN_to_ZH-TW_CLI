import requests
import re

from functools import lru_cache
from parsel import Selector


class Dictionary:
    url = "https://dictionary.cambridge.org/zht/%E6%90%9C%E7%B4%A2/direct/?datasetsearch=english-chinese-traditional&q={}"
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:71.0) Gecko/20100101 Firefox/71.0'
    }

    category_pattern = re.compile(
        r"https://dictionary.cambridge.org/zht/([^/]*)/")

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
            return cls.parse_dictionary_items(resp)

        elif category == 'spellcheck':
            print('spellcheck')
        else:
            raise Exception("not the expect category")  # test

        return resp

    @classmethod
    def parse_dictionary_items(cls, response):
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
                    'pos-header': {
                        'di-title': entry_body_el.css('.pos-header .di-title *::text').get(),
                        'posgram': entry_body_el.css('.pos-header .posgram *::text').get(),
                        'uk-pron': ''.join(entry_body_el.css('.pos-header .uk .pron ::text').getall()),
                        'us-pron': ''.join(entry_body_el.css('.pos-header .us .pron ::text').getall()),
                    },
                    'pos-body': {
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
                            for sense in entry_body_el.css('.pos-body .dsense')
                        ],
                        'idiom': {
                            'title': entry_body_el.css('.pos-body [class*="idiom"] ::text').get(),
                            'items': [
                                {
                                    'item': ''.join(item.css('::text').getall())
                                }
                                for item in entry_body_el.css('.pos-body [class*="idiom"] .item')
                            ],
                        },
                        'phrasal_verb': {
                            'title': entry_body_el.css('.pos-body [class*="phrasal_verb"] h3 ::text').get(),
                            'items': [
                                {
                                    'item': ''.join(item.css('::text').getall())
                                }
                                for item in entry_body_el.css('.pos-body [class*="phrasal_verb"] .item')
                            ],
                        }
                    },
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
