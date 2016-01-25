#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
from os import listdir
from os.path import isfile, join
from py2neo import Graph, Node, Relationship, authenticate
from Fiche import Fiche
import json

def analyseRelations(nom_fichier, dossier, graph):
    # On récupère les associations marqueurs/nom_fichier
    assoc_dict = {}
    with open(join(dossier,'assoc_files')) as f_assoc:
        for line in f_assoc:
            marqueur, filename = line.strip('\n').split(";")
            assoc_dict[marqueur] = filename
    # On crée les liens dans Neo4j à partir du fichier links.json
    # TODO faire une barre de progression ?
    # La boucle de création de liens prend une éternité (~6h pour 300k liens)
    # Problème de performance de Neo4j (je ne crois pas)? Python (je crois) ?
    # Solution : construire une grosse requête Cypher (pour chaque mot clé par exemple) et diminuer le nombre d'appels
    with open(join(dossier, nom_fichier)) as f:
        content = json.loads(f.read())
        for keyword in content:
            for links in content[keyword]:
                creationLiens(keyword, assoc_dict[links['fiche_a']], assoc_dict[links['fiche_b']], links['tf_idf'], graph)

def creationLiens(motcle, fiche_id, fiche_liee_id, poids, graph):
    # Récupérer les noeuds du graphe correspondant aux fiches à lier
    print('TEST :' + fiche_id + '; liee : ' + fiche_liee_id)
    node1 = graph.find_one('Fiche_descriptive', property_key='doc_position', property_value=fiche_id)
    node2 = graph.find_one('Fiche_descriptive', property_key='doc_position', property_value=fiche_liee_id)
    print('Node 1 : ' + str(node1.exists) + ' uri 1 : ' + str(node1.uri))
    print('Node 2 : ' + str(node2.exists) + ' uri 2 : ' + str(node2.uri))
    #Créer la relation correspondantes
    rel = Relationship.cast(node1, (motcle, {"complement": '',"ponderation": poids}), node2)
    # Créer le lien dans neo4j
    graph.create(rel)
    print('OK')



def main(fichier_relations, dossier, ignore_files):
    authenticate("localhost:7474", "neo4j", "haruspex")
    graph_db = Graph()

    # Pour chaque fiche de mots-clés, analyser son contenu
    # et créer les liens correspondants par cooccurrence de mot-clés
    # avec les autres fiches
    analyseRelations(fichier_relations, dossier, graph_db)

if __name__ == "__main__":
    project_directory = sys.argv[1]
    dossier = os.path.join(project_directory, "output")
    fichier_relations = "links.json"
    ignore_files = []
    main(fichier_relations, dossier, ignore_files)
