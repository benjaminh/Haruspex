#!/usr/bin/env python3
# encoding: utf-8
import os
import logging
import re
import json
from csv import writer
import copy
import requests
from ANA_useful import build_wordset, str_simplify
from time import sleep, time, gmtime, strftime
try:
    import treetaggerwrapper#to create a catégory 'is a verb' in output
except ImportError:
    print('ALERT no treetagger install for this python version')



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
    for nuc_idi in [idi for idi in CAND if type(CAND[idi]) == 'ANA_Objects.Nucleus']:
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

def second_wiki_query(cand_idi_bywikishape, dict_candshape, to_decidelater, visitedportals, proxies, lang, headers, baserequest, density2):
    '''
    check if a page in desambiguation categorie can be desambiguate,
    based on the mainly used portals, if the page belongs to them, we choose them!
    '''
    if lang=='fr':
        wiki = "https://fr.wikipedia.org/w/api.php"
    if lang=='en':
        wiki = "https://en.wikipedia.org/w/api.php"
    denominator = max(visitedportals.values())#three portals is allready much enough
    sliced_keys = [to_decidelater[i:i+density2] for i in range(0, len(to_decidelater), density2)]#slicing the big list in sublists for wiki API
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

def first_wiki_query(dict_candshape, proxies, lang, headers, baserequest, density1):
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

    sliced_keys = [keys[i:i+density1] for i in range(0, len(keys), density1)]#slicing the big list in sublists for wiki API
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
    if config['request']['request_wikipedia']:
        baserequest = {}
        baserequest['action'] = 'query'
        baserequest['format'] = 'json'
        baserequest['maxlag'] = '8'
        baserequest['redirects'] = '1'
        baserequest['utf8'] = '1'
        baserequest['formatversion'] = 'latest'
        density1 = config['request']["first_request_density"]
        density2 = config['request']["second_request_density"]

        print('\nSearching on wikipedia for categories, portails, normalized shapes...')
        proxies = config['request']['proxies']
        headers = {'Api-User-Agent':'Haruspex/0.2 (https://github.com/benjaminh/Haruspex/tree/Haruspex2; matthieu.quantin@ec-nantes.fr)'}
        lang = config['lang']
        dict_candshape, to_decidelater, visitedportals, cand_idi_bywikishape = first_wiki_query(dict_candshape, proxies, lang, headers, baserequest, density1)

        if config['request']['try_desambiguation']:
            print('\ntrying_desambiguation on wikipedia for', len(to_decidelater), 'keywords')
            dict_candshape = second_wiki_query(cand_idi_bywikishape, dict_candshape, to_decidelater, visitedportals, proxies, lang, headers, baserequest, density2)


#TODO improve this function that only works on the final shape of the cand and does the job a minima...
def merge_similar_cands(dict_candshape, CAND, OCC):
    simplshape_dict = {}
    Rwordsinline = re.compile(r'(\w+[’|’|\']?|[:.,!?;])(?siu)')
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
    row.append(config['extract']["propernouns_based_search"])
    row.append(isTreetaggerInstalled)#is treetagger installed?
    row.append(len(CAND))
    # allwords = [word for word in dict_candshape[idi]["max_occ_shape"].split() for idi in dict_candshape]
    allwords = [word for idi in dict_candshape for word in dict_candshape[idi]["max_occ_shape"].split()]
    # [item for sublist in l for item in sublist]
    row.append(len(allwords))
    row.append(int(ending))
    row.append(config['steps']["global_steps"])
    row.append(config['steps']["nucleus_nestedsteps"])
    row.append(config['steps']["recession_threshold"])
    row.append(config['steps']["nucleus_threshold"])
    corpus_name = re.sub(r'/ANA/?$', '', os.getcwd())
    corpus_name = re.sub(r'^.*/', '', corpus_name)
    row.append(corpus_name)#get the currend workingdirectory, get the corpus folder name
    row.append(config["lang"])
    with open(config["survey_csvfilepath"], 'a') as csvfile:
        surveyfile = writer(csvfile)
        surveyfile.writerow(row)



def write(CAND, OCC, PAGES, config):
    print('\n\n###### all steps')
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
