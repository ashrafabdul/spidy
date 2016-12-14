'''
Created on Nov 10, 2016

@author: AshrafAbdul
'''


# Generates item classes
def generate_item_classes(items):
    item_classes = []
    # 1 Generate item class for each item
    for item in items:
        
        # 2.1 Get item name
        item_class = []
        item_name = item.find('.//name').text
        item_class.append('\n')
        item_class.append('class '+item_name+'(scrapy.Item):\n')
        
        # 2.2 Get item fields
        field_names = item.findall('.//field/name')
        for field_name in field_names:
            item_class.append('\t'+field_name.text +' = scrapy.Field()\n')

        # 2.3 Add field for storing crawl sequence
        item_class.append('\tcrawl_sequence = scrapy.Field()\n')
        item_class.append('\n')
    
    # 3. Add to item classes
    item_classes += item_class
    
    return item_classes


def generate_spider_class(spider):
    spider_class = []
    start_requests_method = []
    parse_methods = []
    
    # 1. Get the name of the spider
    name = spider.find('.//name').text
    spider_class.append('class '+name+'Spider(scrapy.Spider):\n')
    spider_class.append('\tname = '+'\''+ name.lower()+'\'\n')
    
    # 2 Get the item
    start_requests_method.append('\n\tdef start_requests(self):\n')

    items = spider.findall('.//item')
    
    for item in items:
        item_parse_methods = []

        # 1 Generate start method
        name = item.find('.//name').text
        start_url = item.find('.//startUrl').text
        start_requests_method.append('\t\tyield scrapy.Request('+ '\''+ start_url +'\'' +',self.parse_'+name.lower()+'_1)\n')

        # Get maximum crawl sequence
        crawl_sequences = item.findall('.//field/page/crawlSequence')
        max_sequence = max([c.text for c in crawl_sequences])
        for i in range(1,int(max_sequence)+1):
            
            item_parse_methods.append('\n\tdef parse_'+name.lower()+'_'+str(i)+'(self,response):\n')

            # Find fields
            fields = []
            pages = item.findall('.//page/[crawlSequence='+'\''+str(i)+'\''+']')
            for page in pages:
                fields.append(page.getparent())
            
            # Generate item object
            item_code = []
            if i == 1:
                item_code.append('i = '+name+'()\n')
            else:
                item_code.append('i = response.meta[\'item\']\n')

            # Generate yield
            yield_code = []
            if i == int(max_sequence):
                yield_code.append('yield i\n')
            else:
                yield_code.append('request = scrapy.Request(response.urljoin(crawl_sequence['+str(i+1)+']),callback=self.parse_'+name.lower()+'_'+str(i+1)+')\n')
                yield_code.append('request.meta[\'item\'] = i\n')
                yield_code.append('yield request\n')
                
            # Generate pagination
            pagination_code = []
            pagination = item.find('.//pagination/[crawlSequence='+'\''+str(i)+'\''+']')
            if pagination is not None:
                pagination_xpath = pagination.find('.//xpath').text
                pagination_code.append('\t\tnext_page_urls = response.xpath('+'\''+ pagination_xpath +'\''+').extract()\n')
                pagination_code.append('\t\tfor url in next_page_urls:\n')
                pagination_code.append('\t\t\tyield scrapy.Request(response.urljoin(url),self.parse_'+name.lower()+'_'+str(i)+')\n')

            fragments = item.findall('.//page/fragmentXpath')
            fragment_code = []
            
            direct_code = []
            
            crawl_code = []
            if i == 1:
                crawl_code.append('crawl_sequence = {}\n')
            else:
                crawl_code.append('crawl_sequence = i[\'crawl_sequence\']\n')
            
            for field in fields:
                
                field_name = field.find('.//name').text
                field_xpath = field.find('.//page/fieldXpath').text
                fragment_xpath = field.find('.//page/fragmentXpath')
                is_crawl_url = field.find('.//isCrawlUrl')

                if fragment_xpath is not None:
                    fragment_code.append('\t\t\ti['+'\''+field_name+'\''+'] = fragment.xpath('+'\''+field_xpath+'\''+').extract()\n')
                else:
                    direct_code.append('\t\ti['+'\''+field_name+'\''+'] = response.xpath('+'\''+field_xpath+'\''+').extract()\n')
            
                if is_crawl_url is not None:
                    next_sequence = is_crawl_url.find('.//crawlSequence').text
                    crawl_code.append('crawl_sequence['+next_sequence+'] = i['+'\''+field_name+'\''+'][0]\n')
            
            # save crawl sequence
            crawl_code.append('i[\'crawl_sequence\'] = crawl_sequence\n')
            
            if(fragment_code):
                
                # Generate the for loop for fragment
                item_parse_methods.append('\t\tfor fragment in response.xpath('+'\''+fragments[0].text+'\''+'):\n')
                
                # Adjust indent for item declaration
                item_code = ['\t\t\t'+cl for cl in item_code]

                # Add intend for direct xpath extraction
                if direct_code:
                    direct_code = ['\t'+cl for cl in direct_code]
                    
                # Adjust indent for crawl sequence code
                crawl_code = ['\t\t\t'+cl for cl in crawl_code]
                    
                # adjust indent for yield code
                yield_code = ['\t\t\t'+cl for cl in yield_code]
            
            else:
                
                # Adjust indent for item declaration
                item_code = ['\t\t'+cl for cl in item_code]
            
                # Adjust indent for crawl sequence code
                crawl_code = ['\t\t'+cl for cl in crawl_code]
                
                # adjust indent for yield code
                yield_code = ['\t\t'+cl for cl in yield_code]            
            
            item_parse_methods = item_parse_methods + item_code + fragment_code + direct_code + crawl_code + yield_code + pagination_code
             
    spider_class = spider_class + start_requests_method + item_parse_methods
    return spider_class


def generate_pipeline_class(host, port, user, pwd, db_name, collection_name, on_dup, keys):
    lines = list()
    lines.append("import pymongo\n")
    lines.append("import datetime\n\n\n")
    lines.append("class MongoPipeline(object):\n\n")
    lines.append("\tdef __init__(self):\n")
    lines.append("\t\tself.host = '{0}'\n".format(host))
    lines.append("\t\tself.port = {0}\n".format(port))
    lines.append("\t\tself.user = '{0}'\n".format(user))
    lines.append("\t\tself.pwd = '{0}'\n".format(pwd))
    lines.append("\t\tself.db_name = '{0}'\n".format(db_name))
    lines.append("\t\tself.on_duplicate = '{0}'\n".format(on_dup))
    lines.append("\t\tself.collection_name = '{0}'\n".format(collection_name))
    lines.append("\t\tself.keys = [")
    for key in keys:
        lines.append(" '{0}',".format(key))
    lines.append("]\n\n")

    lines.append("\tdef open_spider(self, spider):\n")
    lines.append("\t\tself.client = pymongo.MongoClient(self.host, self.port)\n")
    lines.append("\t\tself.db = self.client[self.db_name]\n")
    lines.append("\t\tself.db.authenticate(self.user, self.pwd)\n\n")

    lines.append("\tdef close_spider(self, spider):\n")
    lines.append("\t\tself.client.close()\n\n")

    lines.append("\tdef process_item(self, item, spider):\n")
    lines.append("\t\titem = self._convert_keys_to_string(dict(item))\n")
    lines.append("\t\titem['crawl_datetime'] = datetime.datetime.now()\n")
    lines.append("\t\tself.store(item, spider)\n")
    lines.append("\t\treturn item\n\n")

    lines.append("\tdef store(self, item, spider):\n")
    lines.append("\t\tfilter = self._getFilter(item)\n")
    lines.append("\t\tif self.db[self.collection_name].find(filter).count() > 0:\n")
    lines.append("\t\t\tif self.on_duplicate == 'stop':\n")
    lines.append("\t\t\t\tspider.crawler.engine.close_spider(self, 'Duplicated item found.')\n")
    lines.append("\t\t\telif self.on_duplicate == 'update':\n")
    lines.append("\t\t\t\tself.db[self.collection_name].update(filter, {'$set': item }, multi=True)\n")
    lines.append("\t\t\telif self.on_duplicate == 'ignore': pass\n")
    lines.append("\t\t\telse : raise ValueError('Invalid on duplicate action.')\n")
    lines.append("\t\telse:\n")
    lines.append("\t\t\tself.db[self.collection_name].insert(item)\n\n")

    lines.append("\tdef _getFilter(self,item):\n")
    lines.append("\t\tfilter = dict()\n")
    lines.append("\t\tfor key in self.keys:\n")
    lines.append("\t\t\tfilter[key] = item[key]\n")
    lines.append("\t\treturn filter\n\n")

    lines.append("\tdef _convert_keys_to_string(self, d):\n")
    lines.append("\t\tr = {}\n")
    lines.append("\t\tfor key in d:\n")
    lines.append("\t\t\tif type(d[key]) is dict:\n")
    lines.append("\t\t\t\tr[str(key)] = self._convert_keys_to_string(d[key])\n")
    lines.append("\t\t\telse:\n")
    lines.append("\t\t\t\tr[str(key)] = d[key]\n")
    lines.append("\t\treturn r\n\n")
    return lines
