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
import json
import re
import glob
import os
from collections import Counter, defaultdict

def post_supervisedkeys():
    modifs = json.loads(open('output/final_keywords.json').read())
    change_keys = {}
    make_keys = set() # a set is better in case of ducplicates and provides a faster access to check
    remove_keys = set()
    for key in modifs:
        if key['modification'] == 'modifie':
            if '\\' not in key[nouveau_mot_cle]:
                change_keys[key] = key[nouveau_mot_cle]
        if key['modification'] == 'nouveau':
            make_keys.add(key)
        if key['modification'] == 'supprime':
            remove_keys.add(key)
    return change_keys, make_keys, remove_keys


def clean_thedicts():
    pages_name = glob.glob("pages/fiche*.txt")
    # pages_number = [re.findall(r'([\_|\d]+)', page_name) for page_name in pages_name]
    pages_number = list(map(lambda page_name: re.findall(r'([\_|\d]+)', page_name)[0], pages_name))
    ghosts = list(set(dict_bypage) - set(pages_number))
    for ghost in ghosts:
        del dict_bypage[ghost]
        for keyword, pages in dict_bykey.items():
            if ghost in pages:
                pages.remove(ghost)


def inherit_thedicts():
    pages_name = glob.glob("pages/fiche*.txt")
    # pages_number = [re.findall(r'([\_|\d]+)', page_name) for page_name in pages_name]
    pages_number = list(map(lambda page_name: re.findall(r'([\_|\d]+)', page_name)[0], pages_name))
    ghosts = list(set(dict_bypage) - set(pages_number))
    ghosts.pop('0_0_0')
    for ghost in ghosts:
        childs = set()
        parent1 = re.findall(r'(\d)(?=_0_0)', ghost)
        parent2child(parent1[0])
        if parent1:
            parent1 = parent1[0]
            parent1keys = dict_bykey[parent1 + '_0_0'].pop()
            child1_regex = parent1 + '\d_\d'
            for page in dict_bypage:
                if re.match(child_regex, page):
                    dict_bypage[page].extend(parent1keys)
                    childs.append(page)
            for key in parent1keys:
                dict_bykey[key].extend(childs)

        parent2 = re.findall(r'(\d_[^0])(?=_0)', ghost)
        if parent2:
            parent2 = parent2[0]
            parent2keys = dict_bykey[parent2 + '_0'].pop()
            child2_regex = parent2 + '_\d'
            for page in dict_bypage:
                if re.match(child2_regex, page):
                    dict_bypage[page].extend(parent2keys)
                    childs.append(page)
            for key in parent1keys:
                dict_bykey[key].extend(childs)

#build a flex regex to find the new keyword in the pages
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
    return newkeys_regex #newkeys_regex is a dict build this way "hamspam_key_regex":"user_defined_hamspam_key"

def check4keyword_inpage(page_name, newkeys_regex):
    keywords = []
    i = 0
    with open(page_name, 'r', encoding = 'utf8') as page:
        text = page.read()
        for key_regex in newkeys_regex:
            keys = re.findall(key_regex, text)
            for i in range(0,len(keys)):
                keywords.append(newkeys_regex[key_regex])#if the keyword is found thanks to its regex pattern (flexible) then the user defined key shape is added to a list
    return keywords #list of "user_defined_keys" found in a page

def make_keyword(newkeys_regex):
    pages_name = glob.glob("pages/fiche*.txt")
    for page_name in pages_name:
        keywords_inpage = check4keyword_inpage(page_name, newkeys_regex)
        if keywords_inpage != []:
            page_number = re.findall(r'([\_|\d]+)', page_name)
            dict_bypage[page_number].extend(keywords_inpage) # add the new found keywords to the existing dict
            for keyword in keywords_inpage:
                dict_bykey[keyword].append(page_number)
## end of functions to add keywords to keypages, if the user added new keywords
#######################################################################
#######################################################################

def tagging_pages(dict_occ_ref, inherit_keys = False):
    global dict_bypage
    dict_bypage = defaultdict(list)
    global dict_bykey
    dict_bykey = defaultdict(list)

    change_keys, make_keys, remove_keys = post_supervisedkeys() # get the user preferences from a csv file
    page_number = '0_0_0'
    #TODO verifier que la fonction sorted fonctionne bien.
    for pos in sorted(dict_occ_ref):
        value = dict_occ_ref[pos]
        if value[1] == 'v':
            if re.match(r'wxcv[\d|_]*wxcv', value[0]):
                page_num = re.findall(r'(?<=wxcv)([\d|_]*)(?=wxcv)', value[0])
                page_number = page_num[0]
                #keypage_name = 'output/keyword_pages/page' + page_number[0] + '.key'
        if value[1] not in ['v', 't'] and value[1] not in remove_keys: #catch cands except removed by user ones.
                if value[1] in change_keys:
                    keyword = change_keys[value[1]] # rename the keyword with the user defined one
                else:
                    keyword = value[1]
                dict_bypage[page_number].append(keyword) #page_number:keywords in page
                dict_bykey[keyword].append(page_number)  #keywords:pages where it is present

    #this two functions below are build in order to manage the keywords related to a page that doesn't exist because toofew words in it (see option of LaTeX2pages)
    if inherit_keys:
        inherit_thedicts()
    else:
        clean_thedicts()

    with open('output/where_keyword.json', 'w') as json_wherekey:
        json.dump(dict_bykey, json_wherekey, ensure_ascii=False, indent=4)
    with open('output/what_inpage.json', 'w') as json_whatinpage:
        json.dump(dict_bypage, json_whatinpage, ensure_ascii=False, indent=4)
