'''
Created on Nov 10, 2016

@author: AshrafAbdul
'''

IMPORT_STATEMENTS = ['import scrapy\n', 'from scrapy_splash import SlotPolicy\n']


def _get_splash_arg_string(wait_time):
    splash_arg = "meta={'splash': {'args': {'html': 1"
    if wait_time != '0':
        splash_arg += ", 'wait': "
        splash_arg += wait_time
    splash_arg += "}, 'slot_policy': SlotPolicy.SCRAPY_DEFAULT}}"
    return splash_arg


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
            item_class.append('\t'+field_name.text + ' = scrapy.Field()\n')

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
    splash_arg = _get_splash_arg_string('0' if spider.find('.//renderingWaitTime') is None else spider.find('.//renderingWaitTime').text)

    for item in items:
        item_parse_methods = []

        # 1 Generate start method
        name = item.find('.//name').text
        start_url = item.find('.//startUrl').text
        start_requests_method.append('\t\tyield scrapy.Request('+ '\''+ start_url +'\'' +',self.parse_'+name.lower()+'_1, ' + splash_arg + ')\n')

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
                yield_code.append('request = scrapy.Request(response.urljoin(crawl_sequence['+str(i+1)+']),callback=self.parse_'+name.lower()+'_'+str(i+1) + ', ' + splash_arg + ')\n')
                yield_code.append('request.meta[\'item\'] = i\n')
                yield_code.append('yield request\n')
                
            # Generate pagination
            pagination_code = []
            pagination = item.find('.//pagination/[crawlSequence='+'\''+str(i)+'\''+']')
            if pagination is not None:
                pagination_xpath = pagination.find('.//xpath').text
                pagination_code.append('\t\tnext_page_urls = response.xpath('+'\''+ pagination_xpath +'\''+').extract()\n')
                pagination_code.append('\t\tfor url in next_page_urls:\n')
                pagination_code.append('\t\t\tyield scrapy.Request(response.urljoin(url),self.parse_'+name.lower()+'_'+str(i) + ', ' + splash_arg + ')\n')

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
                    fragment_code.append('\t\t\ti['+'\''+field_name+'\''+'] = [ x.strip() for x in fragment.xpath(' + '\'' + field_xpath + '\'' + ').extract() if x.strip() ]\n')
                else:
                    direct_code.append('\t\ti[' + '\'' + field_name + '\'' + '] = [ x.strip() for x in response.xpath(' + '\'' + field_xpath + '\'' + ').extract() if x.strip() ]\n')
            
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


def generate_pipeline_class(host, port, user, pwd, db_name, coll_name, on_dup, keys):
    with open('templates/mongo_pipeline_template.t', 'r') as template_file:
        template = template_file.read()
        key_string = ""
        for key in keys: key_string += " '{0}', ".format(key)
        return template.format(host=host,
                               port=port,
                               user=user,
                               db_name=db_name,
                               pwd=pwd,
                               on_dup=on_dup,
                               coll_name=coll_name,
                               keys=key_string)
