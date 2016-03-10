#!/usr/bin/env python3
# encoding: utf-8

#TODO where_keyword and what_inpage as outputs dans ANA2
#TODO tf-idf en tenant compte du csv modéré de ana2
#TODO construire un csv "node_id", "node_id", "ponderation", "titre(validshape)", "categorie"
#TODO csv import dans neo4j
from py2neo import Graph, authenticate
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
        idf = math.log10(nb_pages/len(set(dict_bykey[keyword])))
        dict_idf[keyword] = idf
    return dict_idf

def buildvalidkeyword(working_directory):
    with open(join(working_directory, 'ANA', 'output', 'keywords.csv'), 'r') as csvfile:
        valids = csv.reader(csvfile)
        next(valids)#skip header row
        validkeys = {}
        for row in valids:
            if row[1]:
                validkeys[row[0]] = {'shape': row[1], 'groups' : row[3], 'occurrences' : row[2]}
    return validkeys

def build_links_TFiDF(working_directory, dict_bykey, dict_bypage):
    idf = calculate_idf(dict_bykey, dict_bypage)
    done = set()
    valid_keywords = buildvalidkeyword(working_directory)
    with open(join(working_directory, 'toneo', 'links.csv'), 'w') as csvfile:
        linksfile = csv.writer(csvfile)
        header = ['fichea', 'ficheb', 'keyword', 'tf_idf', 'occurrences', 'groups']
        linksfile.writerow(header)
        for key in dict_bykey: #each key in a page will be a link
            if key in valid_keywords:
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
                            linksfile.writerow([page_number, p_num, valid_keywords[key]['shape'], tfidf, occurrences, group])

def main(working_directory):
    if not exists(join(working_directory, 'toneo')):
        mkdir(join(working_directory, 'toneo'))
    with open(join(working_directory, 'ANA', 'intra','where_keyword.json')) as where_keyword_file:
        dict_bykey = json.loads(where_keyword_file.read())
    with open(join(working_directory, 'ANA', 'intra','what_inpage.json')) as what_inpage_file:
        dict_bypage = json.loads(what_inpage_file.read())
    build_links_TFiDF(working_directory, dict_bykey, dict_bypage)
    print('linksfile have been written')

def upload_relations(working_directory):
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
MERGE (node1)-[r:keyword { name: csvLine.keyword , occurrences : toInt(csvLine.occurrences), weight: toInt(csvLine.tf_idf) , groups: csvLine.groups }]->(node2)
'''.replace('csvfile',csvfile)
    graph_db.cypher.execute(loadquery)



with open('workingdirectory', 'r') as dirfile:
    working_directory = dirfile.readline().rstrip()
main(working_directory)
upload_relations(working_directory)
