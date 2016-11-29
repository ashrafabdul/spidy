from lxml import etree
import sys
from subprocess import call
import ConfigParser
import generate


#Add Mongodb pipeline to scrapy project setting
def edit_project_mongodb_pipeline_setting(name, file):
    with open(file, 'a+') as f:
        f.write("\nITEM_PIPELINES = {'" + name + ".pipelines.MongoPipeline': 300}")

def edit_project_setting(url, file):
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

    schema = etree.XMLSchema(schema_root)
    xmlparser = etree.XMLParser(schema=schema)
    # Load xml
    try:
        with open(config_path + str(sys.argv[1]), 'r') as f:
            spider = etree.fromstring(f.read(), xmlparser)
    except etree.XMLSyntaxError:
        print "XML validation failed"
        sys.exit(1)

    #1. Open Spider File
    name = spider.find('.//name').text.lower()

    #create a project
    if create_project(name, output_path+name) != 0:
        sys.exit(1)

    #generate spider file
    with open(output_path + name + '/' + name + '/spiders/' + name +'.py', 'w+') as f:

        #2 import scrapy
        f.write("import scrapy\n")

        #3 create classes for items
        items = spider.findall('.//item')
        lines = generate.generate_item_classes(items)
        for line in lines:
            f.write(line)

        #4 create class for spider
        lines = generate.generate_spider_class(spider)
        for line in lines:
            f.write(line)

    #5 create Mongo pipeline file
    pipeline_config = spider.find("dbConfig")
    if (pipeline_config is not None):
        with open(output_path + name + '/' + name + '/' + 'pipelines.py', 'w+') as pipline_file:
            lines = generate.generate_pipeline_class(pipeline_config.find("host").text,
                                            pipeline_config.find("port").text,
                                            pipeline_config.find("db_name").text,
                                            pipeline_config.find("collection_name").text)
            for line in lines:
                pipline_file.write(line)

    edit_project_mongodb_pipeline_setting(name, output_path + name + '/' + name + '/' + 'settings.py')
    edit_project_setting(config_deploy_url, output_path + name + '/' + "scrapy.cfg")