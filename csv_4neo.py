#!/usr/bin/env python3
# encoding: utf-8
from py2neo import Graph, authenticate
from py2neo.packages.httpstream import http
import sys
from os.path import join, exists
from os import mkdir
import json
import math
import csv
from collections import Counter


def calculate_idf(dict_bykey, nb_pages):
    dict_idf = {}
    #nb_pages #how many pages there are
    for keyword in dict_bykey:
        specifity = 1.0-(len(set(dict_bykey[keyword]))/nb_pages)**2#in how many documents the key term appears
        # idf = math.log10(nb_pages/len(set(dict_bykey[keyword]))
        dict_idf[keyword] = specifity
    return dict_idf

def merge_equiv(validkeys, equiv):
    for key in equiv:
        validkeys[equiv[key]]['occurrences'] += validkeys[key]['occurrences']
    return validkeys

def getvalidkeyword(working_directory):
    inputcsvfilepath = join(working_directory, 'ANA', 'output', 'keywords.csv')
    equiv = {}
    with open(inputcsvfilepath, 'r') as csvfile:
        valids = csv.reader(csvfile)
        next(valids)#skip header row
        validkeys = {}
        for row in valids:
            if row[1]:
                validkeys[row[0]] = {'shape': row[1], 'wikipedia_shape': row[2],'groups' : row[6],'groups_confidence': row[7], 'occurrences' : int(row[3])}
            if row[8]:
                equiv[row[0]] = row[8]
    validkeysmerged = merge_equiv(validkeys, equiv)
    return validkeysmerged, equiv

def build_2_dicts(working_directory, valid_keywords, equiv):
    with open(join(working_directory, 'ANA', 'intra','where_keyword.json')) as where_keyword_file:
        dict_bykey = json.loads(where_keyword_file.read())
    with open(join(working_directory, 'ANA', 'intra','what_inpage.json')) as what_inpage_file:
        dict_bypage = json.loads(what_inpage_file.read())
    for key in equiv:
        if key in dict_bykey:
            dict_bykey[equiv[key]] += dict_bykey[key]
            del dict_bykey[key]
        if not key in valid_keywords:
            del dict_bykey[key]
    for page, cands_idis in dict_bypage.items():
        supervised = []
        merged = []
        for cand_idi in cands_idis:
            if cand_idi in equiv:
                merged.append(equiv[cand_idi])
            else:
                merged.append(cand_idi)
        for cand_idi in merged:
            if cand_idi in valid_keywords:
                supervised.append(cand_idi)
        # mergedcands_idis = [equiv[cand_idi] if cand_idi in equiv else cand_idi for cand_idi in cands_idis]
        # supervisedcands_idis = [cand_idi if cand_idi in valid_keywords for cand_idi in mergedcands_idis]
        # dict_bypage[page] = supervised
    return dict_bykey, dict_bypage

def build_links_TFiDF(working_directory, dict_bykey, dict_bypage, valid_keywords):
    idf = calculate_idf(dict_bykey, len(dict_bypage))
    done = set()
    with open(join(working_directory, 'toneo', 'links.csv'), 'w') as csvfile:
        linksfile = csv.writer(csvfile)
        header = ['fichea', 'ficheb', 'keyword', 'tf_idf', 'min_occ', 'tot_occ', 'groups', 'groups_confidence']
        linksfile.writerow(header)
        for key in valid_keywords:# in dict_bykey: #each key in a page will be a link
            nb_occurrences_of_key_inpage = Counter(dict_bykey[key]) #return smth like {'pagenumber1': 2 ; 'pagenumber5': 3 ; 'pagenumberx': y}
            for page_number in nb_occurrences_of_key_inpage:
                for p_num in nb_occurrences_of_key_inpage:
                    linked = str(page_number + '@' + p_num)
                    deknil = str(p_num + '@' + page_number)
                    if (page_number != p_num and deknil not in done):
                        tf = float(nb_occurrences_of_key_inpage[p_num] + nb_occurrences_of_key_inpage[page_number])/float(valid_keywords[key]['occurrences'])
                        weight = tf * idf[key]
                        min_occ = min(nb_occurrences_of_key_inpage[p_num], nb_occurrences_of_key_inpage[page_number])
                        done.add(linked)
                        if valid_keywords[key]['groups']:
                            group = valid_keywords[key]['groups']
                        else:
                            group = 'NULL'
                        if valid_keywords[key]['occurrences']:
                            occurrences = valid_keywords[key]['occurrences']
                        else:
                            occurrences = 'NULL'
                        if valid_keywords[key]['groups_confidence']:
                            confidence = valid_keywords[key]['groups_confidence']
                        else:
                            confidence = 'NULL'
                        linksfile.writerow([page_number, p_num, valid_keywords[key]['shape'], weight, min_occ, occurrences, group, confidence])

def build_keywords_links(working_directory, dict_bykey, dict_bypage, valid_keywords):
    '''
    Build a graph where nodes are keywords and edges are the documents where the two connected nodes occured
    '''
    # Create nodes
    with open(join(working_directory, 'toneo', 'nodes.csv'), 'w') as nodescsvfile:
        nodesfile = csv.writer(nodescsvfile)
        header = ['keyword']
        nodesfile.writerow(header)
        for key in valid_keywords:
            nodesfile.writerow([key])

    # Create edges
    done = dict()
    with open(join(working_directory, 'toneo', 'links.csv'), 'w') as csvfile:
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

def main(working_directory, doc_based_graph):
    if not exists(join(working_directory, 'toneo')):
        mkdir(join(working_directory, 'toneo'))
    valid_keywords, equiv = getvalidkeyword(working_directory)
    dict_bykey, dict_bypage = build_2_dicts(working_directory, valid_keywords, equiv)

    if doc_based_graph == True:
        # Create the graph based on documents
        build_links_TFiDF(working_directory, dict_bykey, dict_bypage, valid_keywords)
    else:
        # Create the graph based on keywords
        build_keywords_links(working_directory, dict_bykey, dict_bypage, valid_keywords)
    print('Linksfile has been written')

def upload_relations(working_directory, doc_based_graph):
    http.socket_timeout = 9999
    # Fichea = graph.find_one('Fiche', property_key='doc_position', property_value=page_ida)
    # Fiche = graph.find_one('Fiche', property_key='doc_position', property_value=page_ida)
    csvfile = 'file://'+join(working_directory, 'toneo', 'links.csv')
    print('Now uploading links to neo4j, this may last a little while...')
    authenticate("localhost:7474", "neo4j", "haruspex")
    graph_db = Graph()
    graph_db.cypher.execute("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE r")#delete the existing relationship (MERGE should avoid this but match is much faster...)

    if doc_based_graph == True:
        # Create the graph based on documents
        graph_db.cypher.execute('CREATE CONSTRAINT ON (a:fiche) ASSERT a.doc_position IS UNIQUE')
        loadquery = '''
        USING PERIODIC COMMIT 500
        LOAD CSV WITH HEADERS
        FROM "csvfile" AS csvLine
        MATCH (node1:fiche { doc_position: csvLine.fichea })
        MATCH (node2:fiche { doc_position: csvLine.ficheb })
        CREATE (node1)-[r:keyword { name: csvLine.keyword , wikiname: coalesce(csvLine.wikipedia_shape, "") , occurrences : toInt(csvLine.tot_occ), weight: toFloat(csvLine.tf_idf), min_occ: ToInt(csvLine.min_occ), groups: csvLine.groups, groups_confidence: coalesce(toInt(csvLine.groups_confidence), "")}]->(node2)
        '''.replace('csvfile',csvfile)
        graph_db.cypher.execute(loadquery)
    else:
        # Create the graph based on keywords
        nodescsvfile = 'file://'+join(working_directory, 'toneo', 'nodes.csv')

        # Upload nodes
        graph_db.cypher.execute('CREATE CONSTRAINT ON (a:keyword) ASSERT a.name IS UNIQUE')
        loadquery = '''
        USING PERIODIC COMMIT 500
        LOAD CSV WITH HEADERS
        FROM "csvfile" AS csvLine
        CREATE (node:keyword { name: csvLine.keyword })
        '''.replace('csvfile',nodescsvfile)
        graph_db.cypher.execute(loadquery)

        # Upload edges
        loadquery = '''
        USING PERIODIC COMMIT 500
        LOAD CSV WITH HEADERS
        FROM "csvfile" AS csvLine
        MATCH (node1:keyword { name: csvLine.keyword1 })
        MATCH (node2:keyword { name: csvLine.keyword2 })
        CREATE (node1)-[r:linked_docs { linked_docs: csvLine.linked_docs }]->(node2)
        '''.replace('csvfile',csvfile)
        graph_db.cypher.execute(loadquery)


with open('workingdirectory', 'r') as dirfile:
    working_directory = dirfile.readline().rstrip()

config = json.loads(open(join(working_directory, 'toneo', 'neo4j_config.json')).read())
doc_based_graph = config['doc_based']

main(working_directory, doc_based_graph)
upload_relations(working_directory, doc_based_graph)
