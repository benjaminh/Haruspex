#!/usr/bin/env python3
# encoding: utf-8
from os.path import join, exists
import yaml
import linking_useful
from os import mkdir, chdir

with open('workingdirectory', 'r') as dirfile:
    workingdirectory = dirfile.readline().rstrip()
# chdir(workingdirectory)
if not exists(join(workingdirectory, 'linking')):
    mkdir(join(workingdirectory, 'linking'))
with open('workingdirectory', 'r') as dirfile:
    workingdirectory = dirfile.readline().rstrip()
config = yaml.load(open(join(workingdirectory, 'linking', 'linking_config.yaml')).read())

print("creating pages and keywords objects")
PAGES = linking_useful.build_pages(workingdirectory)
KEYWORDS = linking_useful.build_keywords(workingdirectory, config)
print("creating links objects")
KEYWORDLINKS, UNIQUELINKS = linking_useful.build_links(KEYWORDS, PAGES)
print(len(KEYWORDLINKS)," keyword_links have been created")
print(len(UNIQUELINKS)," unique_links have been created")
print("computing links ponderations")
linking_useful.calc_ponderations(PAGES, KEYWORDS, KEYWORDLINKS, UNIQUELINKS, config)
# write the csv file for fast upload in neo4j
linking_useful.write_csv_files(KEYWORDLINKS, UNIQUELINKS, config, workingdirectory)
# upload the links in neo4j
linking_useful.upload(workingdirectory, PAGES, config)
