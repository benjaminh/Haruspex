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


def calculate_idf(dict_bykey, dict_bypage):
    dict_idf = {}
    nb_pages = len(dict_bypage) #how many pages there are
    for keyword in dict_bykey:
        specifity = len(set(dict_bykey[keyword]))**2#in how many documents the key term appears
        idf = math.log10(nb_pages/specifity)
        dict_idf[keyword] = idf
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

def build_links_TFiDF(working_directory, dict_bykey, dict_bypage, valid_keywords):
    idf = calculate_idf(dict_bykey, dict_bypage)
    done = set()
    with open(join(working_directory, 'toneo', 'links.csv'), 'w') as csvfile:
        linksfile = csv.writer(csvfile)
        header = ['fichea', 'ficheb', 'keyword', 'tf_idf', 'occurrences', 'groups', 'groups_confidence']
        linksfile.writerow(header)
        for key in dict_bykey: #each key in a page will be a link
            nb_occurrences_of_key_inpage = Counter(dict_bykey[key]) #return smth like {'pagenumber1': 2 ; 'pagenumber5': 3 ; 'pagenumberx': y}
            for page_number in nb_occurrences_of_key_inpage:
                for p_num in nb_occurrences_of_key_inpage:
                    linked = str(page_number + '@' + p_num)
                    deknil = str(p_num + '@' + page_number)
                    if (page_number != p_num and deknil not in done):
                        tf = nb_occurrences_of_key_inpage[p_num] + nb_occurrences_of_key_inpage[page_number]
                        tfidf = tf * idf[key]
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
                        linksfile.writerow([page_number, p_num, valid_keywords[key]['shape'], tfidf, occurrences, group, confidence])

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
        dict_bypage[page] = supervised
    return dict_bykey, dict_bypage



def main(working_directory):
    if not exists(join(working_directory, 'toneo')):
        mkdir(join(working_directory, 'toneo'))
    valid_keywords, equiv = getvalidkeyword(working_directory)
    dict_bykey, dict_bypage = build_2_dicts(working_directory, valid_keywords, equiv)
    build_links_TFiDF(working_directory, dict_bykey, dict_bypage, valid_keywords)
    print('linksfile have been written')

def upload_relations(working_directory):
    http.socket_timeout = 9999
    # Fichea = graph.find_one('Fiche', property_key='doc_position', property_value=page_ida)
    # Fiche = graph.find_one('Fiche', property_key='doc_position', property_value=page_ida)
    csvfile = 'file://'+join(working_directory, 'toneo', 'links.csv')
    print('now uploading links to neo4j, this may last a little while...')
    authenticate("localhost:7474", "neo4j", "haruspex")
    graph_db = Graph()
    graph_db.cypher.execute("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE r")#delete the existing relationship (MERGE should avoid this but...)
    graph_db.cypher.execute('CREATE CONSTRAINT ON (a:fiche) ASSERT a.doc_position IS UNIQUE')
    loadquery = '''
USING PERIODIC COMMIT 500
LOAD CSV WITH HEADERS
FROM "csvfile" AS csvLine
MATCH (node1:fiche { doc_position: csvLine.fichea })
MATCH (node2:fiche { doc_position: csvLine.ficheb })
MERGE (node1)-[r:keyword { name: csvLine.keyword , wikiname: coalesce(csvLine.wikipedia_shape, "") , occurrences : toInt(csvLine.occurrences), weight: toInt(csvLine.tf_idf) , groups: csvLine.groups, groups_confidence: coalesce(toInt(csvLine.groups_confidence), "")}]->(node2)
'''.replace('csvfile',csvfile)
    graph_db.cypher.execute(loadquery)



with open('workingdirectory', 'r') as dirfile:
    working_directory = dirfile.readline().rstrip()
main(working_directory)
upload_relations(working_directory)
