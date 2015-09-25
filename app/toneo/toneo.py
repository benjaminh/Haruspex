#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import json
import math
from collections import Counter


def calculate_idf(dict_bykey, dict_bypage):
    dict_idf = {}
    nb_pages = len(dict_bypage) #how many pages there are
    for keyword in dict_bykey:
        idf = math.log10(nb_pages/len(set(dict_bykey[keyword])))
        dict_idf[keyword] = idf
    return dict_idf

def build_links_TFiDF(project_directory, dict_bykey, dict_bypage):
    '''
    Objectif : créer une liste de liens pondérées entre les fiches et relatives à un mot clé
    Sortie: dictionnaire final_links
    final_links =
    {
        motcle : [
            {
                'fiche_a' : fiche_i,
                'fiche_b' : fiche_j,
                'tf_idf' : valeur
            }
        ]
    }
    '''

    idf = calculate_idf(dict_bykey, dict_bypage)
    done = set()
    final_links = {}
    with open(project_directory + '/output/links.json', 'w') as linksfile:
        for key in dict_bykey: #each key in a page will be a link
            final_links[key] = []
            nb_occurrences_of_key_inpage = Counter(dict_bykey[key]) #return smth like {'pagenumber1': 2 ; 'pagenumber5': 3 ; 'pagenumberx': y}
            for page_number in nb_occurrences_of_key_inpage:
                for p_num in nb_occurrences_of_key_inpage:
                    linked = str(page_number + '@' + p_num)
                    deknil = str(p_num + '@' + page_number)
                    if (page_number != p_num and deknil not in done):
                        tf = nb_occurrences_of_key_inpage[p_num] + nb_occurrences_of_key_inpage[page_number]
                        tfidf = tf * idf[key]
                        done.add(linked)
                        final_links[key].append({'fiche_a': page_number, 'fiche_b': p_num, 'tf_idf': tfidf})
        json.dump(final_links, linksfile, ensure_ascii=False, indent=4)
        linksfile.close()

def main(project_directory):
    with open(project_directory + '/output/where_keyword.json') as where_keyword_file:
        dict_bykey = json.loads(where_keyword_file.read())
        where_keyword_file.close()
    with open(project_directory + '/output/what_inpage.json') as what_inpage_file:
        dict_bypage = json.loads(what_inpage_file.read())
        what_inpage_file.close()
    build_links_TFiDF(project_directory, dict_bykey, dict_bypage)

if __name__ == '__main__':
    project_directory = sys.argv[1]
    main(project_directory)
