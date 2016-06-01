#!/usr/bin/env python3
# encoding: utf-8
from py2neo import Graph, authenticate
from py2neo.packages.httpstream import http
from os.path import join, exists
import json
import csv
from linking_Objects import Keyword, KeywordL, UniqueL, Page

def build_pages(workingdirectory):
    '''
    build a PAGES dict, update the page nodes and upload the updates in neo4J
    '''
    PAGES = {}
    with open(join(workingdirectory, 'pages', 'output', 'nodes.csv'), 'r') as csvfile:
        supervisednodes = csv.reader(csvfile)
        header = next(supervisednodes)
        for supervnode in supervisednodes:
            page = Page(p_num = supervnode[1])
            for i, new_att_value in enumerate(supervnode[3:]):# for each new column defined by user
                if header[i+3]:# if the new column has a header title
                    new_att_name = header[i+3]
                else:
                    new_att_name = 'att'+str(i)
                page.atts.update({new_att_name: new_att_value})# update the dist with the found value
            PAGES[supervnode[1]] = page
    return PAGES


def build_where_key_dict(workingdirectory):
    with open(join(workingdirectory, 'ANA', 'intra','where_keyword.json')) as where_keyword_file:
        dict_bykey = json.loads(where_keyword_file.read())
    return dict_bykey

def build_keywords(workingdirectory, config):
    '''
    get the keywords from the csv file the user can have edited
    only their id have to be preserved.
    '''
    where_key = build_where_key_dict(workingdirectory)# page_number not page objects
    inputcsvfilepath = join(workingdirectory, 'ANA', 'output', 'keywords.csv')
    to_merge = set()
    KEYWORDS = {}
    with open(inputcsvfilepath, 'r') as csvfile:
        valids = csv.reader(csvfile)
        next(valids)#skip header row
        for row in valids:
            if row[1]:#if there is a shape (if not then the user deleted it and we do not consider this keyword line)
                KEYWORDS[row[0]] = Keyword(shape= row[1], wiki_shape =row[2], group = row[6], confidence = row[7], pages_list= where_key[row[0]])
            if row[8]:#if asked to merge within another keyword
                to_merge.add(tuple(row[8], row[0]))
    for tup in to_merge:
        KEYWORDS[tup[0]].merge_with(KEYWORDS[tup[1]])
        del KEYWORDS[tup[1]]
    return KEYWORDS


def build_links(KEYWORDS, PAGES):
    KEYWORDLINKS = set()
    UNIQUELINKS = {}
    for key_num, keyword in KEYWORDS.items():
        done = set()
        for page_num in set(keyword.where):
            for page_number in set(keyword.where):
                linked = str(page_number + '@' + page_num)
                deknil = str(page_num + '@' + page_number)
                if (page_number != page_num and deknil not in done):
                    done.add(linked)
                    link = {'keyword': keyword, 'page_obj_s': PAGES[page_num], 'page_obj_t': PAGES[page_number], 'occ_insource': keyword.where.count(page_num) , 'occ_intarget': keyword.where.count(page_number)}
                    new_keylink = KeywordL(link)
                    KEYWORDLINKS.add(new_keylink)
                    if linked in UNIQUELINKS:
                        UNIQUELINKS[linked].sublinks.add(new_keylink)#add the recently created link in the main
                    else:
                        UNIQUELINKS[linked] = UniqueL({'page_obj_s': PAGES[page_num], 'page_obj_t': PAGES[page_number], 'sublink': new_keylink})
    return KEYWORDLINKS, UNIQUELINKS

def calc_ponderations(PAGES, KEYWORDS, KEYWORDLINKS, UNIQUELINKS, config):
    #calc the ponderation
    for keyword in KEYWORDS.values():
        keyword.weightening(len(PAGES), config)
    for keylink in KEYWORDLINKS:
        keylink.calc_ponderation(config)
    for uniquelink in UNIQUELINKS.values():
        uniquelink.calc_ponderation(config)
    #get the extremum values
    max_keylinkponderation = max([keylink.ponderation for keylink in KEYWORDLINKS])
    values = [uniquelink.ponderation for uniquelink in UNIQUELINKS.values()]
    max_uniquelinkponderation = max(values)
    min_uniquelinkponderation = min(values)
    #scale the ponderation
    for keylink in KEYWORDLINKS:
        keylink.scale_pond(0, max_keylinkponderation)
    for uniquelink in UNIQUELINKS.values():
        uniquelink.scale_pond(min_uniquelinkponderation, max_uniquelinkponderation)


def write_csv_files(KEYWORDLINKS, UNIQUELINKS, config, workingdirectory):
    with open(join(workingdirectory, 'linking', 'keylinks.csv'), 'w') as csvfile:
        keylinksfile = csv.writer(csvfile)
        header = ['source', 'target', 'ponderation', 'shape', 'wiki_shape', 'groups', 'groups_confidence', 'totkeyocc', 'min_occ', 'totsharedocc']
        keylinksfile.writerow(header)
        for keylink in KEYWORDLINKS:
            keylink.test_threshold(config)
            keylink.build_line()#only write if passed threshold
            keylink.write_line(keylinksfile)
    with open(join(workingdirectory, 'linking', 'uniquelinks.csv'), 'w') as csvfile:
        uniquelinksfile = csv.writer(csvfile)
        header = ['source', 'target', 'ponderation', 'quantity']
        uniquelinksfile.writerow(header)
        for uniquelink in UNIQUELINKS.values():
            uniquelink.build_line()
            uniquelink.write_line(uniquelinksfile)
    print('Linksfile has been written')



def upload(workingdirectory, PAGES, config):
    http.socket_timeout = 9999
    # Fichea = graph.find_one('Fiche', property_key='doc_position', property_value=page_ida)
    # Fiche = graph.find_one('Fiche', property_key='doc_position', property_value=page_ida)
    print('Now uploading links to neo4j, this may last a little while...')

    authenticate("localhost:7474", config['graph']['user_name'], config['graph']['password'])
    graph_db = Graph()
    graph_db.run("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE r")#delete the existing relationship (MERGE should avoid this barbarism but match is muchMUCH faster...)
    for page in PAGES.values():
        page.upload(graph_db)
    if config['graph']['doc_based'] == True:
        keylinksfile = 'file://'+join(workingdirectory, 'linking', 'keylinks.csv')
        uniquelinksfile = 'file://'+join(workingdirectory, 'linking', 'uniquelinks.csv')
        # keylinksfile = 'file:///keylinks.csv'
        # uniquelinksfile = 'file:///uniquelinks.csv'

        # Create the graph based on documents as nodes
        graph_db.run('CREATE CONSTRAINT ON (a:fiche) ASSERT a.doc_position IS UNIQUE')
        basequery = '''
        USING PERIODIC COMMIT 10000
        LOAD CSV WITH HEADERS
        FROM "csvfile" AS csvLine
        MATCH (node1:fiche { doc_position: csvLine.source })
        MATCH (node2:fiche { doc_position: csvLine.target })'''
        # specify the query for the keylinks
        keylinkquery = basequery.replace('csvfile',keylinksfile) + '\nCREATE (node1)-[r:keyword { name: csvLine.shape , wikiname: coalesce(csvLine.wiki_shape, "") , occurrences : toInt(csvLine.totkeyocc), ponderation: toFloat(csvLine.ponderation), min_occ: ToInt(csvLine.min_occ), shared_occ: ToInt(csvLine.totsharedocc), groups: csvLine.groups, groups_confidence: coalesce(toFloat(csvLine.groups_confidence), "")}]->(node2)'
        graph_db.run(keylinkquery)
        # specify the query for the unique links
        uniquelinkquery = basequery.replace('csvfile',uniquelinksfile) + ' CREATE (node1)-[r:unique { ponderation: toFloat(csvLine.ponderation), quantity: toInt(csvLine.quantity)}]->(node2)'
        graph_db.run(uniquelinkquery)
    else:
        # Create the graph based on keywords
        nodescsvfile = 'file://'+join(workingdirectory, 'linking', 'nodes.csv')
        # Upload nodes
        graph_db.run('CREATE CONSTRAINT ON (a:keyword) ASSERT a.name IS UNIQUE')
        loadquery = '''
        USING PERIODIC COMMIT 500
        LOAD CSV WITH HEADERS
        FROM "csvfile" AS csvLine
        CREATE (node:keyword { name: csvLine.keyword })
        '''.replace('csvfile',nodescsvfile)
        graph_db.run(loadquery)

        # Upload edges
        loadquery = '''
        USING PERIODIC COMMIT 500
        LOAD CSV WITH HEADERS
        FROM "csvfile" AS csvLine
        MATCH (node1:keyword { name: csvLine.keyword1 })
        MATCH (node2:keyword { name: csvLine.keyword2 })
        CREATE (node1)-[r:linked_docs { linked_docs: csvLine.linked_docs }]->(node2)
        '''.replace('csvfile',csvfile)
        graph_db.run(loadquery)















def build_documentlinks(workingdirectory, dict_bykey, dict_bypage, valid_keywords):
    '''
    Build a graph where nodes are keywords and edges are the documents where the two connected nodes occured
    '''
    # Create nodes
    with open(join(workingdirectory, 'linking', 'nodes.csv'), 'w') as nodescsvfile:
        nodesfile = csv.writer(nodescsvfile)
        header = ['keyword']
        nodesfile.writerow(header)
        for key in valid_keywords:
            nodesfile.writerow([key])

    # Create edges
    done = dict()
    with open(join(workingdirectory, 'linking', 'links.csv'), 'w') as csvfile:
        linksfile = csv.writer(csvfile)
        header = ['source', 'target', 'linked_docs']
        linksfile.writerow(header)
        # Step 1 : list all the pages in which the keyword occurrences
        # Step 2 : for each page in the list at step 1, list all the keywords in this page
        # Step 3 : remove duplicates and count the number of linked docs
        total = len(valid_keywords)
        indicator = 0
        for key in valid_keywords:# in dict_bykey: #each key in a page will be a node
            indicator += 1
            nb_occurrences_of_key_inpage = Counter(dict_bykey[key]) #return smth like {'pagenumber1': 2 ; 'pagenumber5': 3 ; 'pagenumberx': y}
            assoc_keywords = dict()
            for page_number in nb_occurrences_of_key_inpage:
                assoc_keywords[page_number] = set(dict_bypage[str(page_number)])
                for keyword in assoc_keywords[page_number]:
                    linked = str(key) + '@' + str(keyword)
                    deknil = str(keyword) + '@' + str(key)
                    if (keyword != key and linked not in done and deknil not in done):
                        done[linked] = 1
                    elif (keyword != key and linked in done):
                        done[linked] += 1
                    elif (keyword != key and deknil in done):
                        done[linked] = done[deknil] + 1
                        del done[deknil]
            if indicator == total/4:
                print('25%  done')
            elif indicator == total/2:
                print('50%  done')
            elif indicator == (total*3)/4:
                print('75%  done')
            elif indicator >= total:
                print('100%  done')

        for assoc in done:
            key,keyword = assoc.split('@')
            linked_docs = done[assoc]
            linksfile.writerow([valid_keywords[key]['shape'], valid_keywords[keyword]['shape'], linked_docs])
