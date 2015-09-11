#!/usr/bin/env python3
# encoding: utf-8

'''
Post_processing functions will not affect the dict_occ_ref but only the tagging pages.
The user via GUI produces a csv file, based on the final cands list.
this file is:
state [rm, ch, mk],  anafound_cand (str),    user_defined_cand (str)

with:
rm: removed keyword by user
ch: changed keyword by user
mk: make a new keyword exists in text
'''
import csv
import re
import glob
import os

def post_supervisedkeys():
    with open('user_supervised_keywords.csv', 'rt', encoding='utf8') as keywordFile:
        Keyfile = csv.reader(keywordFile, delimiter= ';', quotechar='"')
        change_keys = {}
        make_keys = set() # a set is better in case of ducplicates and provides a faster access to check
        remove_keys = set()
        for row in Keyfile:
            if row[0] == 'ch':
                change_keys[row[1]] = row[2]
            if row[0] == 'mk':
                make_keys.add(row[2])
            if row[0] == 'rm':
                remove_keys.add(row[1])
    return change_keys, make_keys, remove_keys

def create_keyword_page(keypage_name, keywords):
    with open(keypage_name, 'w', encoding = 'utf8') as keypage:
        if keywords != []:
            for keyword in keywords:
                keypage.write(keyword + '\n')

## functions to add keywords to keypages, if the user added new keywords
def add_keyword2keypage(keypage_name, keywords):
    print('trying to add', keywords, 'in', keypage_name)
    with open(keypage_name, 'a', encoding = 'utf8') as keypage:
        if keywords != []:
            for keyword in keywords:
                keypage.write(keyword + '\n')

def build_newkeys_regex(make_keys):
    newkeys_regex = {}
    for key in make_keys:
        valid_keyparts = []
        keyparts = re.findall(r'(\w+[\’|\']?|[.,!?;])(?siu)', key)
        for keypart in keyparts: #exclude the short words
            if len(keypart) >= 3:
                valid_keyparts.append(keypart)
        onekeypattern = r'(.{,4}' + r'.{,10}'.join(valid_keyparts) + r'.{,4})' + '(?iLmsu)'
        onekeyregex = re.compile(onekeypattern)
        newkeys_regex[onekeyregex] = key #dict of compiled regex pattern matching the new cands (user defined ones) with corresponding user defined key
    # newkeys_pattern = "|".join(keypattern_list) + '(?iLmsu)'
    # newkeys_regex = re.compile(newkeys_pattern)
    return newkeys_regex

def check4keyword_inpage(page_name, newkeys_regex):
    keywords = []
    i = 0
    with open(page_name, 'r', encoding = 'utf8') as page:
        text = page.read()
        for key_regex in newkeys_regex:
            keys = re.findall(key_regex, text)
            for i in range(0,len(keys)):
                keywords.append(newkeys_regex[key_regex])#if the keyword is found thanks to its regex pattern (flexible) then the user defined key shape is added to a list
    return keywords

def make_keyword(newkeys_regex):
    pages_name = glob.glob("pages/*.txt")
    for page_name in pages_name:
        if 'fiche' in page_name: #check if the word 'fiche' appears in the file name to avoid catching the 'references' and 'pictures' files
            keywords_inpage = check4keyword_inpage(page_name, newkeys_regex)
            if keywords_inpage != []:
                page_number = re.findall(r'([\_|\d]+)', page_name)
                keypage_name = 'output/keyword_pages/page' + page_number[0] + '.key'
                add_keyword2keypage(keypage_name, keywords_inpage)
## end of functions to add keywords to keypages, if the user added new keywords


def tagging_pages(dict_occ_ref):
    dict_bypage = {}
    change_keys, make_keys, remove_keys = post_supervisedkeys() # get the user preferences from a csv file
    ##build a flex regex to find the new keyword in the pages
    if not os.path.exists('output/keyword_pages/'):
        os.makedirs('output/keyword_pages/')
    page_number = '0.0.0'
    #TODO verifier l'ordre de lecture dans le dico
    for pos, value in dict_occ_ref.items():
        if value[1] == 'v':
            if re.match(r'wxcv[\d|_]*wxcv', value[0]):
                page_number = re.findall(r'(?<=wxcv)([\d|_]*)(?=wxcv)', value[0])
                keypage_name = 'output/keyword_pages/page' + page_number[0] + '.key'
        if value[1] not in ['v', 't'] and value[1] not in remove_keys: #catch cands except removed by user ones.
                if value[1] in change_keys:
                    keyword = change_keys[value[1]] # rename the keyword with the user defined one
                else:
                    keyword = value[1]
                dict_bypage.setdefault(keypage_name, []).append(keyword)

    for keypage_name, keywords in dict_bypage.items():
        create_keyword_page(keypage_name, keywords)
    if make_keys:
        newkeys_regex = build_newkeys_regex(make_keys)
        make_keyword(newkeys_regex)
