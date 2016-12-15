import pymongo
import datetime
import logging
import settings
import uuid
from scrapy import signals


class MongoPipeline(object):
    def __init__(self):
        self.host = '{host}'
        self.port = {port}
        self.user = '{user}'
        self.pwd = '{pwd}'
        self.db_data_name = '{db_name}'
        self.db_stat_name = 'crawl_stats'
        self.on_duplicate = '{on_dup}'
        self.collection_name = '{coll_name}'
        self.keys = [{keys}]
        self.client = pymongo.MongoClient(self.host, self.port)

        try: self.job_id = spider._job
        except AttributeError: self.job_id = str(uuid.uuid4())

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def open_spider(self, spider):
        self._init_stats(spider)
        self._select_data_db()

    def process_item(self, item, spider):
        item = self._convert_keys_to_string(dict(item))
        item['crawl_datetime'] = datetime.datetime.now()
        self._store_item(item, spider)
        return item

    def spider_closed(self, spider):
        self._select_stat_db()
        self._store_stats(spider)
        self.client.close()

    def _store_item(self, item, spider):
        key_filter = self._get_key_filter(item)
        if self.db[self.collection_name].find(key_filter).count() > 0:
            if self.on_duplicate == 'stop':
                spider.crawler.engine.close_spider(self, 'Duplicated item found.')
            elif self.on_duplicate == 'update':
                self.db[self.collection_name].update(key_filter, {{'$set': item}}, multi=True)
                spider.crawler.stats.inc_value('update_item_count')
            elif self.on_duplicate == 'ignore':
                pass
            else:
                raise ValueError('Invalid on duplicate action.')
        else:
            self.db[self.collection_name].insert(item)
            spider.crawler.stats.inc_value('insert_item_count')

    def _store_stats(self, spider):
        stats = spider.crawler.stats.get_stats()
        stats['_id'] = self.job_id
        stats['project'] = settings.BOT_NAME
        stats['spider'] = spider.name
        self._select_stat_db()
        self.db['crawl_stats'].insert(stats)

    def _select_data_db(self):
        self.db = self.client[self.db_data_name]
        self.db.authenticate(self.user, self.pwd)

    def _select_stat_db(self):
        self.db = self.client[self.db_stat_name]
        self.db.authenticate(self.user, self.pwd)

    def _init_stats(self, spider):
        spider.crawler.stats.set_value('update_item_count', 0)
        spider.crawler.stats.set_value('insert_item_count', 0)

    def _get_key_filter(self, item):
        key_filter = dict()
        for key in self.keys:
            key_filter[key] = item[key]
        return key_filter

    def _convert_keys_to_string(self, d):
        r = {{}}
        for key in d:
            if type(d[key]) is dict:
                r[str(key)] = self._convert_keys_to_string(d[key])
            else:
                r[str(key)] = d[key]
        return r

