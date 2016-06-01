#!/usr/bin/env python3
# encoding: utf-8
import os
import logging
import re
from ANA_Objects import Nucleus, Candidat, Occurrence, Page
import json
from csv import writer
import copy
from time import sleep, time, gmtime, strftime
import multiprocessing


global rm_accent
rm_accent = {'é':'e', 'è':'e', 'ê':'e', 'ë':'e', 'ù':'u', 'û':'u', 'ü':'u','ç':'c', 'ô':'o', 'ö':'o', 'œ':'oe', 'î':'i', 'ï':'i', 'â':'a', 'à':'a', 'ä':'a'}


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
            wordsset |= set([re.sub(r'\n$', '', s.lower()) for s in lines if s!='\n' ])
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

def build_regex(wordlist_file_path):
    wordset = build_wordset(wordlist_file_path)
    regexlist = [word.strip() + '.?.?' if len(word)>3 and not re.findall(r'\\|\.|\*|\+', word) else word.strip() for word in wordset]#two extra last characters are authorized except for allready regex or shortwords
    if regexlist:
        regex = r'|'.join(regexlist) + r'(?siu)'
        return re.compile(regex)
    else:
        return re.compile(' ')#FIXME I need a regex that will never match, a None regex, here the space will never match since we process only words

def str_simplify(string):
    '''remove accents and comon final french letters "e", "s", "ent"'''
    ascii_shape = ''.join([rm_accent[caract] if caract in rm_accent else caract for caract in string.lower()]) #if charac in the dict of accentuated charact, then replace it by its non-accentuated match
    ascii_shape = re.sub(r's$', '', ascii_shape)#remove final s of the word
    ascii_shape = re.sub(r'e$', '', ascii_shape)#remove final e
    ascii_shape = re.sub(r'nt$', '', ascii_shape)#remove final nt
    return ''.join(ascii_shape)


def start_log(working_directory):
    logfilepath = os.path.join(working_directory, 'log', 'ana.log')
    logging.basicConfig(filename=logfilepath, format='%(levelname)s:%(message)s', level=logging.INFO)
    logging.info('Started at' + str(strftime("%a, %d %b %Y %H:%M:%S", gmtime())))

def slicelist(liste, slicelen=False, slicenum=False):
    #slicing the list in sublists
    if not slicelen:
        slicelen = int(len(liste)/slicenum)+1
    return [liste[i:i+slicelen] for i in range(0, len(liste), slicelen)]

def worker(idis, candidats, occurrences, queue):
    """processor parallel worker function"""
    toupdate = {}
    for idi in idis:
        where, occ_repr, shape_repr = candidats[idi].buildnuc(occurrences, candidats)
        toupdate[idi] = {'where': where, 'occ_repr': occ_repr, 'shape_repr': shape_repr}
        queue.put(toupdate)
    return

def rejoindata(results, CAND, OCC):
    for idi in results:
        CAND[idi].where = results[idi]['where']
        CAND[idi].occ_represent = results[idi]['occ_repr']
        CAND[idi].shape_represent = results[idi]['shape_repr']
        CAND[idi].build(OCC, CAND)#transform the twords in nucleus

def queustayempty(q):
    stayempty = False
    step = 0.05
    duration = 2
    while not duration == 0 or not q.empty():
        sleep(step)
        duration-=step
    if duration == 0:
        stayempty = True
    return stayempty


def dispatch_buildnuc(newnucs_idis, CAND, OCC):
    '''
    newnucs_idis is a list of CAND id for new nuc
    this function dispatch the newnucleuses search on several processors
    this is the heaviest operation. Needs to be multiproc
    '''
    cpunum = len(os.sched_getaffinity(0))
    q = multiprocessing.Queue()
    parts = slicelist(liste=newnucs_idis, slicenum=cpunum)
    proc = {}
    sleeptime = 4/cpunum#TODO verify this value... expermiental, empirical
    for i in range(cpunum):
        if i < len(parts):
            proc[i] = multiprocessing.Process(target=worker, args=(parts[i], CAND, OCC, q))
            proc[i].start()
    results = {}
    waited = 0
    reduced = False
    while True:
        sleep(0.1)
        waited+=1
        if waited == 10:
            break
        if not q.empty():
            break
    while not q.empty():
        while not q.empty():
        #item in queue should be dict of dict/ key: cand_idi; value: {'where': where, 'occ_repr': occ_repr, 'shape_repr': shape_repr}
            results.update(q.get())#there should not be any duplicate...
        sleeptime = 10/(q.qsize()+1)
        if sleeptime < 1:
            sleep(sleeptime)
        else:
            sleep(1)
    for i in range(cpunum):
        if i < len(parts):
            proc[i].join()#waiting for each processor to finish
    rejoindata(results, CAND, OCC)
    del results

def buildinlang(Haruspexdir, config):
    if config["lang"] == "fr":
        emptywords = build_wordset(os.path.join(Haruspexdir, 'french', 'emptywords_fr.txt'))
        stopwords = build_wordset(os.path.join(Haruspexdir, 'french', 'stopwords_fr.txt'))
        linkwords = build_linkdict(os.path.join(Haruspexdir, 'french', 'schema'))
    if config["lang"] == "en":
        emptywords = build_wordset(os.path.join(Haruspexdir, 'english', 'emptywords_en.txt'))
        stopwords = build_wordset(os.path.join(Haruspexdir, 'english', 'stopwords_en.txt'))
        linkwords = build_linkdict(os.path.join(Haruspexdir, 'english', 'schema'))
    return emptywords, stopwords, linkwords

#jsonpagespos_path is to store the position of the markers spliting the original pages in the concatenated txt4ana.txt
def build_OCC(Haruspexdir, working_directory, config):
    start_log(working_directory)
    logging.info('### building the OCC dict ###')
    occ2boot = {}
    propernouns = {}
    emptywords, stopwords, linkwords = buildinlang(Haruspexdir, config)
    bootstrap = build_bootdict(os.path.join(working_directory, 'bootstrap'))
    Rextraemptyword = build_regex(os.path.join(working_directory, "extra_emptywords.txt"))
    Rextrastopword = build_regex(os.path.join(working_directory, "extra_stopwords.txt"))
    Rwordsinline = re.compile(r'(\w+[’|’|\']?|[:.,!?;])(?siu)')
    Rsplitermark = re.compile(r'wxcv[\d|_]*wxcv')
    Rdate = re.compile(r'(1\d\d\d|20\d\d)')
    Rnumeral = re.compile(r'(\b\d+\b)')
    Rponctuation = re.compile(r'[,!?;]')
    dotahead = False
    index = 0
    page_id = None#initial state to catch the first marker (see below)
    PAGES = {}# dict {key:id of the page, value: Page object)
    OCC = {}
    CAND = {}
    with open(os.path.join(working_directory, 'txt4ana'), 'r', encoding = 'utf8') as txtfile:
        for line in txtfile:
            words = Rwordsinline.findall(line)
            for word in words:
                index += 1
                matchbootstrap = False
                if Rsplitermark.match(word):
                    if page_id:#the first markers of the page will not close a previous page
                        PAGES[page_id].where += (index,)#close the previous page, the var page_id is still the previous version
                    page_id = re.findall(r'([\_|\d]+)', word)[0]#get the new page id
                    PAGES[page_id] = Page(begin=index+1, idi=page_id)#a page object, init "where" with begining of the next page
                    index -= 1#otherwise there is a missing OCC key in the OCC dict
                elif word.lower() in linkwords:
                    OCC[index] = Occurrence(long_shape = word, linkword = linkwords[word.lower()])
                    dotahead = False
                elif word.lower() in stopwords or Rextrastopword.match(word):
                    OCC[index] = Occurrence(long_shape = word, stopword = True)
                    if re.match(r'\.|\?|\!', word):
                        dotahead = True
                elif word.lower() in emptywords or Rnumeral.match(word) or Rponctuation.match(word) or Rextraemptyword.match(word):
                    OCC[index] = Occurrence(long_shape = word)
                    dotahead = False
                elif Rdate.match(word):#IDEA is it interesting to have dates as tword?
                    OCC[index] = Occurrence(long_shape = word, date = True, tword = True)
                    dotahead = False
                else:
                    OCC[index] = Occurrence(long_shape = word, tword = True)
                    for indice in bootstrap:#bootstrap is a dict Occurrences objects
                        if OCC[index].soft_equality(bootstrap[indice]):
                            occ2boot.setdefault(indice, set()).add(tuple([index]))#index as tuple to easily build normal cand position (allways a tuple of positions)
                            matchbootstrap = True#not be in conflict with the propernouns below
                            continue
                    if dotahead == False and word[0].isupper() and words.index(word) != 0 and matchbootstrap == False:#no dot before and uppercase and not begining of a newline -> it is a propernoun
                        simplshape = str_simplify(word)#to avoid differences like Échalas / ECHALAS  (they'll build to branches and never merge until the end)
                        propernouns.setdefault(simplshape, set()).add(tuple([index]))
    newnucs_idis = []
    if page_id:
        PAGES[page_id].where += (index,)#closing the last page
    for indice in occ2boot:# building the cand from the all the occ matching with bootstrap words
        try:
            next_id = max(CAND)+1
        except ValueError:#this means it is the first cand, there is no value for max
            next_id = 1
        CAND[next_id] = Nucleus(idi = next_id, where = occ2boot[indice])
        newnucs_idis.append(next_id)
    if config['extract']['propernouns']:#if the config file ask for building the propernouns as Candidates (Nucleus)
        for propernoun in propernouns:
            if len(propernouns[propernoun])>=config['extract']["propernouns_threshold"]:#if more than one occurrence of the propernoun has been found
                try:
                    next_id = max(CAND)+1
                except ValueError:#this means it is the first cand, there is no value for max, so there is no bootstrap cand
                    print('ALERT: No word in bootstrap file...')
                    next_id = 1
                CAND[next_id] = Nucleus(idi = next_id, where = propernouns[propernoun])
                if config['extract']["propernouns_based_search"]:
                    newnucs_idis.append(next_id)
                else:
                    CAND[next_id].build(OCC, CAND)
    dispatch_buildnuc(newnucs_idis, CAND, OCC)
    return OCC, CAND, PAGES
