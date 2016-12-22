from lxml import etree
import sys
from subprocess import call
import ConfigParser
import generate
import fileinput
import re


# Add Mongodb pipeline to scrapy project setting
def edit_spider_setting(name, setting_file, splash_url):
    for line in fileinput.input(setting_file, inplace=True):
        if re.match("^\s*ROBOTSTXT_OBEY\s*=\s*.*$", line):
            print "ROBOTSTXT_OBEY = False"
        else:
            print line
    setting = "\n\nITEM_PIPELINES = {\n\t'" + name + ".pipelines.MongoPipeline': 300\n}\n\n"
    setting += "EXTENSIONS = {\n\t'scrapy.extensions.feedexport.FeedExporter': None \n}\n\n"
    setting += "SPIDER_MIDDLEWARES = {\n\t'scrapy_splash.SplashDeduplicateArgsMiddleware': 100 \n}\n\n"
    setting += "DOWNLOADER_MIDDLEWARES = {\n\t'scrapy_splash.SplashCookiesMiddleware': 723,\n\t'scrapy_splash.SplashMiddleware': 725,\n\t'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810, \n}\n\n"
    setting += "DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'\n\n"
    setting += "HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'\n\n"
    setting += "SPLASH_URL = '" + splash_url + "'\n\n"
    with open(setting_file, 'a+') as f:
        f.write(setting)


def edit_scrapy_setting(url, file):
    with open(file, 'a+') as f:
        f.write("url = " + url)
    lines = []
    with open(file) as infile:
        for line in infile:
            lines.append(line.replace("#", ";"))
    with open(file, 'w') as outfile:
        for line in lines:
            outfile.write(line)


def create_project(name, path):
    return call(['scrapy', 'startproject', name, path])


def get_configs():
    config = ConfigParser.ConfigParser()
    config.read("./config.ini")
    return config

if __name__ == '__main__':
    config = get_configs()
    output_path = config.get('CONFIG', 'OUTPUT_PATH')
    config_path = config.get('CONFIG', 'CONFIG_PATH')
    config_deploy_url = config.get("DEPLOY", "URL")

    # Load XSD
    try:
        with open('./spidy_config.xsd', 'r') as f:
            schema_root = etree.XML(f.read())
    except IOError:
        print "Could not load xsd file"
        sys.exit(1)

    try:
        schema = etree.XMLSchema(schema_root)
        xmlparser = etree.XMLParser(schema=schema)
        # Load xml
        try:
            with open(config_path + str(sys.argv[1]), 'r') as f:
                spider = etree.fromstring(f.read(), xmlparser)
        except etree.XMLSyntaxError as e:
            print "XML validation failed. \nCause: " + e.message
            sys.exit(1)
    except etree.XMLSchemaParseError as e:
        print "XML schema parse error. \nCause: " + e.message
        sys.exit(1)

    # 1. Open Spider File
    name = spider.find('.//name').text.lower()

    # create a project
    if create_project(name, output_path+name) != 0:
        sys.exit(1)

    # generate spider file
    with open(output_path + name + '/' + name + '/spiders/' + name +'.py', 'w+') as f:

        # 2 import
        for line in generate.IMPORT_STATEMENTS:
            f.write(line)

        # 3 create classes for items
        items = spider.findall('.//item')
        lines = generate.generate_item_classes(items)
        for line in lines:
            f.write(line)

        # 4 create class for spider
        lines = generate.generate_spider_class(spider)
        for line in lines:
            f.write(line)

    # 5 create Mongo pipeline file
    db_configs = spider.find("dbConfig")

    # get keys from config file
    keys = list()
    for key in spider.find("item").find("keys").findall("key"):
        keys.append(key.text)

    if db_configs is not None:
        with open(output_path + name + '/' + name + '/' + 'pipelines.py', 'w+') as pipline_file:
            pipeline_content = generate.generate_pipeline_class(db_configs.find("host").text,
                                                     db_configs.find("port").text,
                                                     db_configs.find("username").text,
                                                     db_configs.find("password").text,
                                                     db_configs.find("dbName").text,
                                                     db_configs.find("collectionName").text,
                                                     spider.find("item").find("onDuplicate").text,
                                                     keys)
            pipline_file.write(pipeline_content)
    splash_url = spider.find("splashUrl").text
    edit_spider_setting(name, output_path + name + '/' + name + '/' + 'settings.py', splash_url)
    edit_scrapy_setting(config_deploy_url, output_path + name + '/' + "scrapy.cfg")