#!/usr/bin/env python3
# encoding: utf-8
import os
import logging
import re
from ANA_Objects import Nucleus, Candidat, Occurrence, Page
import json
from csv import writer
import copy
import requests
from time import sleep, time, gmtime, strftime
import multiprocessing
try:
    import treetaggerwrapper#to create a catégory 'is a verb' in output
except ImportError:
    print('ALERT no treetagger install for this python version')

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
    if config['propernouns']:#if the config file ask for building the propernouns as Candidates (Nucleus)
        for propernoun in propernouns:
            if len(propernouns[propernoun])>=config["propernouns_threshold"]:#if more than one occurrence of the propernoun has been found
                try:
                    next_id = max(CAND)+1
                except ValueError:#this means it is the first cand, there is no value for max, so there is no bootstrap cand
                    print('ALERT: No word in bootstrap file...')
                    next_id = 1
                CAND[next_id] = Nucleus(idi = next_id, where = propernouns[propernoun])
                if config["propernouns_based_search"]:
                    newnucs_idis.append(next_id)
                else:
                    CAND[next_id].build(OCC, CAND)
    dispatch_buildnuc(newnucs_idis, CAND, OCC)
    return OCC, CAND, PAGES



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
        dict_candshape[cand_id] = {"max_occ_shape": max_occS, "shortest_shape": shortest_shape, 'Wikipedia_shape': '', 'Wikipedia_portals': ''}
    return dict_candshape

def purge_forbidden_cand(non_solo_file_path, CAND, OCC):
    forbidden_cand_shapes = build_wordset(non_solo_file_path)
    for nuc_idi in [idi for idi in CAND if isinstance(CAND[idi], Nucleus)]:
        for forbidden_shape in forbidden_cand_shapes:
            forbid_occ_instance = Occurrence(forbidden_shape)
            if CAND[nuc_idi].is_forbidden(forbid_occ_instance, OCC):#check in soft eguality with all the shapes of the nucleus
                del CAND[nuc_idi]
                break#once nuc_idi is forbidden, no need to search how many times it could be forbidden...!

def areverbs(dict_candshape, config):
    try:# TreeTagger is optional...
        lang = config["lang"]
        tagger = treetaggerwrapper.TreeTagger(TAGLANG=lang)
        verbpat = 'VER'
        if lang == 'en':
            verbpat = 'VV'
        for idi in dict_candshape:
            tags = tagger.tag_text(dict_candshape[idi]["max_occ_shape"])
            taglist = treetaggerwrapper.make_tags(tags)
            for tag in taglist:
                if re.match(verbpat,tag.pos) and not tag.word[0].isupper():
                    dict_candshape[idi]["verb_based"] = True
                    break
                else:
                    dict_candshape[idi]["verb_based"] = False
        return True
    except:
        print("\nALERT Error during the tagging of VERBS; did you install treeTagger?")
        for idi in dict_candshape:
            dict_candshape[idi]["verb_based"] = 'no TreeTagger'
        return False

def continuewikireq(wiki, parametres, proxies, headers):
    lastContinue = {'continue': ''}
    results = {}
    while True:
            # Modify it with the values returned in the 'continue' section of the last result.
            parametres.update(lastContinue)
            # Call API
            result = requests.get(wiki, params= parametres, proxies=proxies, headers=headers).json()
            if 'error' in result:
                if result['error']['code'] == 'maxlag':
                    print('waiting 5sec for wikipedia server')
                    sleep(4)
                    result['continue']= lastContinue
                else:
                    raise Exception(result['error'])
            if 'warnings' in result:
                print(result['warnings'])
            if 'query' in result:
                results.update(result['query'])
            if 'continue' not in result:
                break
            lastContinue = result['continue']
            if not 'pages' in results:
                print('problem:', parametres, results)
                results['pages'] = []
    return results

def second_wiki_query(cand_idi_bywikishape, dict_candshape, to_decidelater, visitedportals, proxies, lang, headers, baserequest):
    '''
    check if a page in desambiguation categorie can be desambiguate,
    based on the mainly used portals, if the page belongs to them, we choose them!
    '''
    if lang=='fr':
        wiki = "https://fr.wikipedia.org/w/api.php"
    if lang=='en':
        wiki = "https://en.wikipedia.org/w/api.php"
    denominator = max(visitedportals.values())#three portals is allready much enough
    sliced_keys = [to_decidelater[i:i+3] for i in range(0, len(to_decidelater), 3)]#slicing the big list in sublists for wiki API
    request2 = baserequest.copy()
    request2['prop'] = 'links'
    request2['plnamespace'] = '0'
    request2['pllimit'] = '500'
    request3 = request2.copy()
    request3['plnamespace'] = '100'
    highestconfidence = 0
    for sli in sliced_keys:
        if sli:
            request2['titles'] = '|'.join(sli)
            dict_rep2 = continuewikireq(wiki, request2, proxies, headers)
            try:
                for page in dict_rep2['pages']:
                    idi = cand_idi_bywikishape[page['title']]#cand_idi corresponding to the pages
                    if re.search(r'[A-Z_\.]{2,}', page['title']):
                        goodlinks = [link['title'] for link in page['links'] if re.findall(page['title']+'| (?siu)', link['title'])]#composed of several words (separed by space)
                    else:
                        goodlinks = [link['title'] for link in page['links'] if re.findall(page['title']+'(?siu)', link['title'])][:20]#contain page title
                    #if there is more than xx goodlinks then it's a very common name, not useful
                    request3['titles'] = '|'.join(goodlinks)
                    dict_rep3 = continuewikireq(wiki, request3, proxies, headers)
                    max_confidence = 0
                    try:
                        for page in dict_rep3['pages']:
                            portals = [re.sub(r'Po.*?:', '', link['title']) for link in page['links']]
                            confidence = sum([visitedportals[portal] for portal in portals if portal in visitedportals])/(denominator*len(goodlinks)/10)
                            if set(portals) <= set(visitedportals):
                                confidence+=0.2#bonus if nothing out of subject!
                            if confidence > max_confidence:
                                max_confidence = confidence
                                best_portals = portals
                                best_title = page['title']
                            elif max_confidence == 0:
                                best_portals = ''
                                best_title = page['title']
                        dict_candshape[idi]['Wikipedia_portals'] = best_portals
                        dict_candshape[idi]['portals_confidence'] = max_confidence
                        dict_candshape[idi]['Wikipedia_shape'] = best_title
                        if max_confidence > highestconfidence:
                            highestconfidence = max_confidence
                    except KeyError:
                        pass
            except KeyError:
                pass
        sleep(3)
    for idi in dict_candshape:
        try:
            if type(dict_candshape[idi]['portals_confidence']) is float:
                dict_candshape[idi]['portals_confidence'] = dict_candshape[idi]['portals_confidence'] / highestconfidence
        except KeyError:
            pass
    return dict_candshape

def first_wiki_query(dict_candshape, proxies, lang, headers, baserequest):
    '''
    return
    dict_candshape with wikishape: normalized page title by wiki request redirection: cleantitle (str)
    dict_candshape with the wikipedia portals the page belongs to: portnames (list)
    set of pages which request point to a desambiguation page: to_decidelater (set)
    '''
    to_decidelater = []
    visitedportals = {}
    cand_idi_bywikishape = {}
    cand_idi_byshape = {}
    keys = []
    if lang=='fr':
        wiki = "https://fr.wikipedia.org/w/api.php"
        homonym_categories = ['Homonymie','Homonymie+de+patronyme', 'Homonymie+de+personnes', 'Homonymie+de+toponyme',  'Homonymie+de+batailles']
        homonym_categories_str = '|'.join(['Catégorie:'+cat for cat in homonym_categories])
    if lang=='en':
        wiki = "https://en.wikipedia.org/w/api.php"
        homonym_categories_str = 'Category:disambiguation+pages'

    for idi, shapes in dict_candshape.items():
        keyword = re.sub(' ', '_', shapes["max_occ_shape"])
        keys.append(keyword)
        cand_idi_byshape[keyword] = idi#inverted dict to retrieve the idi from the requested wikipage

    sliced_keys = [keys[i:i+50] for i in range(0, len(keys), 50)]#slicing the big list in sublists for wiki API
    for sli in sliced_keys:
        request1 = baserequest.copy()
        # request1.update(baserequest)#get the root data for all the requests
        request1['prop'] = 'categories|links'
        request1['titles'] = '|'.join(sli)
        request1['clcategories'] = homonym_categories_str
        request1['cllimit'] = '500'
        request1['plnamespace'] = '100'
        request1['pllimit'] = '500'
        dict_rep = continuewikireq(wiki, request1, proxies, headers)
        #keeping the cand_idi in relation with the mutation of the wikipage
        if 'normalized' in dict_rep:
            for item in dict_rep['normalized']:
                cand_idi_bywikishape[item['to']] = cand_idi_byshape[item['from']]
                del(cand_idi_byshape[item['from']])
        cand_idi_bywikishape.update(cand_idi_byshape)#get all the other shape that have not been normalized, because they where corrects
        if 'redirects' in dict_rep:
            for item in dict_rep['redirects']:
                cand_idi_bywikishape[item['to']] = cand_idi_bywikishape[item['from']]
                del(cand_idi_bywikishape[item['from']])
        for page in dict_rep["pages"]:
            if 'missing' in page:
                continue
            idi = cand_idi_bywikishape[page['title']]#cand_idi corresponding to the page
            dict_candshape[idi]['Wikipedia_shape'] = page['title']
            if 'categories' in page:
                to_decidelater.append(page['title'])
                dict_candshape[idi]['portals_confidence'] = 'not decided'
            elif 'pageid' in page and 'links' in page:
                portals = [re.sub(r'Po.*?:','', link['title']) for link in page['links']]
                dict_candshape[idi]['Wikipedia_portals'] = portals
                #TODO calculate a better confidence on the portals if the page exists
                for portal in portals:
                    visitedportals.setdefault(portal, 0)
                    visitedportals[portal]+=1
    return dict_candshape, to_decidelater, visitedportals, cand_idi_bywikishape

def get_wikidata(dict_candshape, CAND, config):
    if config['request_wikipedia']:
        baserequest = {}
        baserequest['action'] = 'query'
        baserequest['format'] = 'json'
        baserequest['maxlag'] = '8'
        baserequest['redirects'] = '1'
        baserequest['utf8'] = '1'
        baserequest['formatversion'] = 'latest'

        print('\nSearching on wikipedia for categories, portails, normalized shapes...')
        proxies = config['proxies']
        headers = {'Api-User-Agent':'Haruspex/0.2 (https://github.com/benjaminh/Haruspex/tree/Haruspex2; matthieu.quantin@ec-nantes.fr)'}
        lang = config['lang']
        dict_candshape, to_decidelater, visitedportals, cand_idi_bywikishape = first_wiki_query(dict_candshape, proxies, lang, headers, baserequest)

        if config['try_desambiguation']:
            print('\ntrying_desambiguation on wikipedia for', len(to_decidelater), 'keywords')
            dict_candshape = second_wiki_query(cand_idi_bywikishape, dict_candshape, to_decidelater, visitedportals, proxies, lang, headers, baserequest)


#TODO improve this function that only works on the final shape of the cand and does the job a minima...
def merge_similar_cands(dict_candshape, CAND, OCC):
    simplshape_dict = {}
    for idi in dict_candshape:
        simpl_shape = ' '.join([str_simplify(word) for word in Rwordsinline.findall(dict_candshape[idi]["max_occ_shape"])])
        simplshape_dict.setdefault(simpl_shape, []).append(idi)
    for shape in simplshape_dict:
        if len(simplshape_dict[shape])>1:
            tomerge_idis = simplshape_dict[shape][1:]
            CAND[simplshape_dict[shape][0]].merge(tomerge_idis, CAND)#merge the first cand with all the similar ones
            for cand_id in tomerge_idis:
                del dict_candshape[cand_id]
                del CAND[cand_id]

def match_candpage(PAGES, CAND, OCC):
        for cand_idi in CAND:
            for occ_positions in CAND[cand_idi].where:#self.where is a set of tuple, -> occ_positions is a tupe
                for page_idi in PAGES:
                    if PAGES[page_idi].where[0] < occ_positions[0] < PAGES[page_idi].where[1]:
                        PAGES[page_idi].what.append(cand_idi)
                        CAND[cand_idi].whichpage.append(page_idi)


def writesurvey(config, CAND, dict_candshape, ending, isTreetaggerInstalled):
#row: version date	CPUnum	txtlenght(Mo)	Prop.noun search	Treetagger	Final cand nb	tot. word cand nb	lasted step	nesteedstep	threshold	corpus name	lang
    row = []
    row.append(str(strftime("%d/%m/%Y", gmtime())))#date
    row.append(len(os.sched_getaffinity(0)))#cpunum
    row.append(os.path.getsize("txt4ana"))#txt4ana lengh
    row.append(config["propernouns_based_search"])
    row.append(isTreetaggerInstalled)#is treetagger installed?
    row.append(len(CAND))
    # allwords = [word for word in dict_candshape[idi]["max_occ_shape"].split() for idi in dict_candshape]
    allwords = [word for idi in dict_candshape for word in dict_candshape[idi]["max_occ_shape"].split()]
    # [item for sublist in l for item in sublist]
    row.append(len(allwords))
    row.append(int(ending))
    row.append(config["global_steps"])
    row.append(config["nucleus_nestedsteps"])
    row.append(config["recession_threshold"])
    row.append(config["nucleus_threshold"])
    corpus_name = re.sub(r'/ANA/?$', '', os.getcwd())
    corpus_name = re.sub(r'^.*/', '', corpus_name)
    row.append(corpus_name)#get the currend workingdirectory, get the corpus folder name
    row.append(config["lang"])
    with open(config["survey_csvfilepath"], 'a') as csvfile:
        surveyfile = writer(csvfile)
        surveyfile.writerow(row)



def write_output(CAND, OCC, PAGES, config):
    print('candidats trouvés :', len(CAND))
    ending = time() - config["started_at"]
    print('ana lasted: ', str(ending), ' seconds')
    logging.info('Ended at' + str(ending))

    purge_forbidden_cand('non_solo.txt', CAND, OCC)#check throught soft eguality if a CAND shape is in the forbidden list
    dict_candshape = cand_final_shapes(CAND, OCC)
    merge_similar_cands(dict_candshape, CAND, OCC)
    isTreetaggerInstalled = areverbs(dict_candshape, config)
    get_wikidata(dict_candshape, CAND, config)
    match_candpage(PAGES, CAND, OCC)
    if os.path.isfile(config["survey_csvfilepath"]):
        writesurvey(config, CAND, dict_candshape, ending, isTreetaggerInstalled)
    else:
        print("ALERT: no survey file path mentionned, don't you want to add one?")
    alone = {}
    wherekey = {}
    print('\n\n###### writting output files')
    for cand_id, candid in CAND.items():
        if len(set(candid.whichpage)) == 1:
            alone[cand_id] = True
        else:
            alone[cand_id] = False
        wherekey[cand_id] = candid.whichpage
    inpage = {page_id: page.what for page_id, page in PAGES.items()}
    # for page_id, page in PAGES.items():
    #     inpage[page_id] = page.what
    with open('intra/where_keyword.json', 'w') as where_keyword:
        json.dump(wherekey, where_keyword, ensure_ascii=False, indent=4)
    with open('intra/what_inpage.json', 'w') as what_inpage:
        json.dump(inpage, what_inpage, ensure_ascii=False, indent=4)
    with open('output/keywords.csv', 'w') as csvfile:
        keyfile = writer(csvfile)
        header = [
        'cand_id',
        'max occurring shape',
        'Wikipedia_shape',
        'occurrences',
        'in only 1 fiche',
        'is_verb_based',
        'groups',
        'groups confidence ([0-1])',
        'merge with'
        ]
        keyfile.writerow(header)
        for idi in CAND:
            keyfile.writerow([
            idi,
            dict_candshape[idi].get("max_occ_shape"),
            dict_candshape[idi].get("Wikipedia_shape"),
            len(CAND[idi].where),
            alone[idi],
            dict_candshape[idi].get("verb_based"),
            ','.join(dict_candshape[idi].get('Wikipedia_portals')),
            dict_candshape[idi].get('portals_confidence'),
            ''
            ])
    ending2 = time() - config["started_at"] - ending
    print('writing output lasted: ', str(ending2), ' seconds')
