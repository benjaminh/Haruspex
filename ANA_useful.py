#!/usr/bin/env python3
# encoding: utf-8
import os
import logging
import re
from ANA_Objects import Nucleus, Candidat, Occurrence, Page
import json
import copy

global rm_accent
rm_accent = {'é':'e', 'è':'e', 'ê':'e', 'ë':'e', 'ù':'u', 'û':'u', 'ü':'u','ç':'c', 'ô':'o', 'ö':'o', 'œ':'oe', 'î':'i', 'ï':'i', 'â':'a', 'à':'a', 'ä':'a'}
Rwordsinline = re.compile(r'(\w+[’|’|\']?|[:.,!?;])(?siu)')

def setupfolder():
    if not os.path.exists('output/'):
        os.makedirs('output/')#keywords, what_in_page, where_keyword...
    if not os.path.exists('log/'):
        os.makedirs('log/')#log, stuff
    elif os.path.isfile('log/ana.log'):
        os.remove('log/ana.log')
    if not os.path.exists('intra/'):
        os.makedirs('intra/')#mapping, pages_pos,

def merge_dicts(dict_list):
    result = {}
    for dictionary in dict_list:
        result.update(dictionary)
    return result

def merge_egal_sple_dict(OCC, *dict_args):
    '''
    input dict {key: occurrence_position, value: whatever}
      - given any number of dicts, shallow copy and merge into a new dict,
      - occurrence position have to be referenced in OCC dict (bridge the occ_position and the shapes...)
    output dict {key: tuple of equal_keys, values: list of equal values}
      - based on egal_sple fonction.
    '''
    final = {}
    if len(dict_args) > 1:
        merged = merge_dicts(dict_args)
    else:
        merged = dict_args[0]

    if len(merged) == 1: # faster if there is only one pair of (key, value) in the dict!
        key, value = merged.popitem()
        final[(key,)] = [value]
        return final
    else:
        equal = {}
        for key1 in merged:
            equal[key1] = set([key1])
            # equal_keys = (key1,)
            # equal_values = (merged[key1],)#tuple init, not set because maybe duplicates
            for key2 in merged:
                if key2 not in equal and OCC[key1].soft_equality(OCC[key2]):
                    equal[key1].add(key2)#equal[occ_pos] = set of occ_pos
        # now: FOAF style "les amis de mes amis sont mes amis..."
        # 1 degree only! should be enough
        z = {}
        seen = set()
        for key in sorted(equal, key=lambda k: len(equal[k]), reverse = True):#equal[occ_pos] = set of occ_pos
            if key not in seen:
                seen.update(equal[key])
                z[key] = copy.copy(equal[key])#copy of the equal[key] entry
                for key_eq in equal[key]:
                    z[key].update(equal[key_eq])# add all the foaf without duplication (in a set)
                    seen.update(equal[key_eq])# only one degree so we can don't want to rebuild the whole dict of relations.
        # now lets build the dict[equal_keys] = equal_values
        for key, key_eqs in z.items():
            for key_eq in key_eqs:
                final.setdefault(tuple(key_eqs), []).append(merged[key_eq])# retrieves the value of the original dict to merge in soft eq
        return final


def count_nuc_cases(value_eq):# merged = list of tuples(link_word_type, cand_id) for equivalent twords
#{merged[tuple of (occurrence_position)]: list of tuples(cand_id, link_word_type)}
# Four Cases!
    s1 = 0# s1: same linkword same CAND
    s2 = 0# s2: same linkword, different CAND
    s3 = 0# s3: different linkword, same CAND
    s4 = 0# s4: different linkword, different CAND
    seen = set()
    for i, feature in enumerate(value_eq):#feature is tuple(cand_id, link_word_type)
        link_word_type, cand_id = feature
        seen.add(i)
        for i2, feature2 in enumerate(value_eq):
            if i2 not in seen:
                link_word_type2, cand_id2 = feature2
                if cand_id2 != cand_id and link_word_type2 == link_word_type:
                    s2 += 1
                elif cand_id2 == cand_id and link_word_type2 == link_word_type:
                    s1 += 1
                elif cand_id2 == cand_id and link_word_type2 != link_word_type:
                    s3 += 1
                elif cand_id2 != cand_id and link_word_type2 != link_word_type:
                    s4 += 1
    return (s1, s2, s3, s4)

def build_bootdict(bootstrap_file_path):
    with open(bootstrap_file_path, 'r', encoding='utf8') as bootstrapfile:
        text = bootstrapfile.read()
        cands = re.split('\W+', text)
        bootstrap = {}
        for i, cand in enumerate(cands):
            if cand:
                bootstrap[i] = Occurrence(long_shape = cand, cand = 0, cand_pos = set(), date = False, linkword = 0, tword = True)
        return bootstrap

def build_wordset(*args):#arg should be a file path
    wordsset = set()
    for wordlist_file_path in args:
        with open(wordlist_file_path, 'r', encoding='utf8') as wordlistfile:
            lines = wordlistfile.readlines()
            wordsset |= (set([re.sub(r'\n', '', s.lower()) for s in lines]))
    return wordsset

def build_linkdict(linkwords_file_path):# basicaly in french {de:1, du:1, des:1, d:1, au:2, aux:2, en:3}
    with open(linkwords_file_path, 'r', encoding = 'utf8') as linkwordsfile:
        lines = linkwordsfile.readlines()
        linkwords = {}
        for i, line in enumerate(lines):
            line = re.sub('\s+$', '', line)
            line = re.split('\W+', line)
            for linkword in line:
                linkwords[linkword] = i+1# to avoid having the first line considered as 0 index; Actualy 0 is for non-linkwords
        return linkwords


#jsonpagespos_path is to store the position of the markers spliting the original pages in the concatenated txt4ana.txt
def build_OCC(txt4ana, stopwords_file_path, extra_stopwords_file_path, emptywords_file_path, extra_emptywords_file_path, linkwords_file_path, bootstrap_file_path, match_propernouns, working_directory):
    bootstrap = build_bootdict(bootstrap_file_path)
    occ2boot = {}
    propernouns = {}
    emptywords = build_wordset(emptywords_file_path, extra_emptywords_file_path)
    stopwords = build_wordset(stopwords_file_path, extra_stopwords_file_path)
    linkwords = build_linkdict(linkwords_file_path)
    Rsplitermark = re.compile(r'wxcv[\d|_]*wxcv')#TODO build a splitermark regex
    Rdate = re.compile(r'(1\d\d\d|20\d\d)')
    Rnumeral = re.compile(r'(\b\d+\b)')
    Rponctuation = re.compile(r'[,!?;]')
    dotahead = False
    index = 0
    page_id = None#initial state to catch the first marker (see below)
    PAGES = {}# dict {key:id of the page, value: Page object)
    OCC = {}
    CAND = {}
    with open(txt4ana, 'r', encoding = 'utf8') as txtfile:
        for line in txtfile:
            words = Rwordsinline.findall(line)
            for word in words:
                index += 1
                matchbootstrap = False
                if Rsplitermark.match(word):
                    #TODO page_id = get the id of the splitmarker, or build it
                    if page_id:#the first markers of the page will not ask to close a previous page
                        PAGES[page_id].where += (index,)#close the previous page, the var page_id is still the previous version
                    page_id = re.findall(r'([\_|\d]+)', word)[0]#get the new page id
                    PAGES[page_id] = Page(begin=index+1, idi=page_id)#a page object, init "where" with begining of the next page
                    index -= 1#otherwise there is a missing OCC key in the OCC dict
                elif word in linkwords:
                    OCC[index] = Occurrence(long_shape = word, linkword = linkwords[word])
                    dotahead = False
                elif word.lower() in stopwords:
                    OCC[index] = Occurrence(long_shape = word, stopword = True)
                    if re.match(r'\.|\?|\!', word):
                        dotahead = True
                elif Rdate.match(word):#IDEA is it interesting to have dates as tword?
                    OCC[index] = Occurrence(long_shape = word, date = True, tword = True)
                    dotahead = False
                elif word.lower() in emptywords or Rnumeral.match(word) or Rponctuation.match(word):
                    OCC[index] = Occurrence(long_shape = word)
                    dotahead = False
                else:
                    OCC[index] = Occurrence(long_shape = word, tword = True)
                    for indice in bootstrap:#bootstrap is a dict Occurrences objects
                        if OCC[index].soft_equality(bootstrap[indice]):
                            occ2boot.setdefault(indice, set()).add(tuple([index]))
                            matchbootstrap = True#not be in conflict with the propernouns below
                            continue
                    if dotahead == False and word[0].isupper() and words.index(word) != 0 and matchbootstrap == False:#no dot before and uppercase and not begining of a newline -> it is a propernoun
                        propernouns.setdefault(word, set()).add(tuple([index]))
        if page_id:
            PAGES[page_id].where += (index,)#closing the last page
        for indice in occ2boot:# building the cand from the all the occ matching with bootstrap words
            try:
                next_id = max(CAND)+1
            except ValueError:#this means it is the first cand, there is no value for max
                next_id = 1
            CAND[next_id] = Nucleus(idi = next_id, where = occ2boot[indice])
            CAND[next_id].buildnuc(OCC, CAND)
        if match_propernouns:
            for propernoun in propernouns:
                if len(propernouns[propernoun])>1:#if more than one occurrence of the propernoun has been found
                    try:
                        next_id = max(CAND)+1
                    except ValueError:#this means it is the first cand, there is no value for max, so there is no bootstrap cand
                        print('ALERT: No word in bootstrap file...')
                        next_id = 1
                    CAND[next_id] = Nucleus(idi = next_id, where = propernouns[propernoun])
                    CAND[next_id].buildnuc(OCC, CAND)#
    return OCC, CAND, PAGES
                #FIXME how to build Atelier et Chantier if Atelier and Chantier are allready cands -> no linkword, nothing helps to build it!
                #TODO build neo4j nods corresponding to the pages. (should have been done before, in preANA step)

def str_simplify(string):
    '''remove accents and comon final french letters "e", "s", "ent"'''
    ascii_shape = ''.join([rm_accent[caract] if caract in rm_accent else caract for caract in string.lower()]) #if charac in the dict of accentuated charact, then replace it by its non-accentuated match
    ascii_shape = re.sub(r's$', '', ascii_shape)#remove final s of the word
    ascii_shape = re.sub(r'e$', '', ascii_shape)#remove final e
    ascii_shape = re.sub(r'nt$', '', ascii_shape)#remove final nt
    return ''.join(ascii_shape)

def cand_final_shapes(CAND, OCC):
    #dict_candshape is a dict {key: cand_id ; value: {"max_occ_shape": "str"; "shortest_shape": "str"; DBpediashape }
    dict_candshape = {}
    for cand_id in CAND:
        shortest_shape = ''.join([str(x) for x in range(50)])
        max_occ_shape = {}
        for cand_pos in CAND[cand_id].where:
            shape = ' '.join([OCC[occ_pos].long_shape for occ_pos in cand_pos])
            max_occ_shape.setdefault(shape, 0)
            max_occ_shape[shape] += 1
            if len(shortest_shape) > len(shape):
                shortest_shape = shape
        for shape in sorted(max_occ_shape, key=max_occ_shape.get, reverse = True):
            max_occS = shape
            break
        dict_candshape[cand_id] = {"max_occ_shape": max_occS, "shortest_shape": shortest_shape, "DBpediashape": None }
    return dict_candshape

def areforbidden(non_solo_file_path, CAND, OCC):
    forbidden_cand_idi = set()
    forbidden_cand_shapes = build_wordset(non_solo_file_path)
    for nuc_idi in [idi for idi in CAND if isinstance(CAND[idi], Nucleus)]:
        for forbidden_shape in forbidden_cand_shapes:
            forbid_occ_instance = Occurrence(forbidden_shape)
            if CAND[nuc_idi].is_forbidden(forbid_occ_instance, OCC):#check in soft eguality with all the shapes of the nucleus
                forbidden_cand_idi.add(nuc_idi)
                break#once nuc_idi is forbidden, no need to search how many times it is forbidden...!
    return forbidden_cand_idi

#TODO improve this function that only works on the final shape of the cand and does the job a minima...
def merge_similar_cands(dict_candshape, CAND, OCC):
    simplshape_dict = {}
    for idi in dict_candshape:
        simpl_shape = ' '.join([str_simplify(word) for word in Rwordsinline.findall(dict_candshape[idi]['shortest_shape'])])
        simplshape_dict.setdefault(simpl_shape, []).append(idi)
    for shape in simplshape_dict:
        if len(simplshape_dict[shape])>1:
            tomerge_idis = simplshape_dict[shape][1:]
            CAND[simplshape_dict[shape][0]].merge(tomerge_idis, CAND)#merge the first cand with all the similar ones
            for cand_id in tomerge_idis:
                del dict_candshape[cand_id]
                del CAND[cand_id]
    return CAND, dict_candshape




def write_output(CAND, OCC, PAGES):
    forbid_cand_id_set = areforbidden('non_solo.txt', CAND, OCC)#check throught soft eguality if a CAND shape is in the forbidden list
    dict_candshape = cand_final_shapes(CAND, OCC)
    CAND, dict_candshape = merge_similar_cands(dict_candshape, CAND, OCC)
    inpage = {}
    wherekey = {}
    for page_idi in PAGES:
        page_end = PAGES[page_idi].where[1]
        page_begin = PAGES[page_idi].where[0]
        for cand_idi in CAND:
            if cand_idi not in forbid_cand_id_set:#if this a Nucleus of the non_solo
                for where in CAND[cand_idi].where:#self.where is a set of tuple, -> where is a tupe
                    if page_begin < where[0] < page_end:
                        inpage.setdefault(page_idi, []).append(cand_idi)
                        wherekey.setdefault(cand_idi, []).append(page_idi)
    print('\n\n###### writting output')
    print('\nKEYWORDS that won\'t build links because they come from only ONE FICHE')
    for cand_idi, pages_occs in wherekey.items():
        pageset = set(pages_occs)
        if len(pageset) == 1:
            print(pageset.pop(), '-', str(len(CAND[cand_idi].where)), '-', dict_candshape[cand_idi]["max_occ_shape"])
    with open('intra/where_keyword.json', 'w') as where_keyword:
        json.dump(wherekey, where_keyword, ensure_ascii=False, indent=4)
    with open('intra/what_inpage.json', 'w') as what_inpage:
        json.dump(inpage, what_inpage, ensure_ascii=False, indent=4)
    with open('output/keywords.csv', 'w') as keyfile:
        keyfile.write('cand_id, max occurring shape, occurrences, groups\n')
        for idi in CAND:
            if idi not in forbid_cand_id_set:
                keyfile.write(str(idi)+','+ dict_candshape[idi]["max_occ_shape"]+','+str(len(CAND[idi].where))+','+','+'\n')
