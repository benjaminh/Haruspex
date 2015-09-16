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
from collections import Counter

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

def create_keyword_page(keypage_number, keywords):
    keypage_name = 'output/keyword_pages/page' + page_number + '.key'
    with open(keypage_name, 'w', encoding = 'utf8') as keypage:
        if keywords != []:
            for keyword in keywords:
                keypage.write(keyword + '\n')

#######################################################################
#######################################################################
## functions to add keywords to keypages, if the user added new keywords
def add_keyword2keypage(page_number, keywords):
    keypage_name = 'output/keyword_pages/page' + page_number + '.key'
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
    pages_name = glob.glob("pages/*.txt")
    for page_name in pages_name:
        if 'fiche' in page_name: #check if the word 'fiche' appears in the file name to avoid catching the 'references' and 'pictures' files
            keywords_inpage = check4keyword_inpage(page_name, newkeys_regex)
            if keywords_inpage != []:
                page_number = re.findall(r'([\_|\d]+)', page_name)
                add_keyword2keypage(page_number, keywords_inpage)
                dict_bypage[page_number].extend(keywords_inpage) # add the new found keywords to the existing dict
                [dict_bykey[keyword].append(page_number) for keyword in keywords_inpage]
## end of functions to add keywords to keypages, if the user added new keywords
#######################################################################
#######################################################################

def tagging_pages(dict_occ_ref):
    global dict_bypage = defaultdict(list)
    global dict_bykey = defaultdict(list)
    change_keys, make_keys, remove_keys = post_supervisedkeys() # get the user preferences from a csv file
    ##build a flex regex to find the new keyword in the pages
    if not os.path.exists('output/keyword_pages/'):
        os.makedirs('output/keyword_pages/')
    page_number = '0.0.0'
    #TODO verifier l'ordre de lecture dans le dico - fait
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

    for page_number, keywords in dict_bypage.items():
        create_keyword_page(page_number, keywords)
    if make_keys:
        newkeys_regex = build_newkeys_regex(make_keys)
        make_keyword(newkeys_regex)

#TODO think about the usefulness of the files .key if it' only display or if the user can handwrite a new keyword in it.
#also if its about adding new keyword, maybe the GUI is more usefull to do this (than opening a file and write manualy)
#so this can be done without a file (adding new keyword -> the GUI also can provide access to the dict_bypage and dict_bykey?)
#TODO clean the problem of .key file related to pages that haven't been created (because too few words)
#choose option? enable user to choose an option?

def idf():
    idf = {}
    nb_pages = len(dict_bypage) #how many pages there are
    for keyword in dict_bykey:
        idf = math.log10(nb_pages/len(set(dict_bykey[keyword])))
        idf[keyword] = idf
    return idf

def build_links_TFiDF():
    idf = idf()
    done = set()
    with open('links.csv') as linksfile:
        for key in dict_bykey: #each key in a page will be a link
            nb_occurrences_of_key_inpage = Counter(dict_bykey[key]) #return smth like {'pagenumber1': 2 ; 'pagenumber5': 3 ; 'pagenumberx': y}
            for page_number in nb_occurrences_of_key_inpage:
                for p_num in nb_occurrences_of_key_inpage:
                    linked = str(page_number + '@' + p_num)
                    deknil = str(p_num + '@' + page_number)
                    if (page_number != p_num and deknil not in done):
                        tf = nb_occurrences_of_key_inpage[p_num] + nb_occurrences_of_key_inpage[page_number]
                        tfidf = tf*idf[key]
                        done.append(linked)
                        link = linked + key + str(tfidf)
                        linksfile.write(link)
