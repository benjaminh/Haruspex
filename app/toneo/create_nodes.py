#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
from os import listdir
from os.path import isfile, join
from py2neo import Graph, Node, Relationship, authenticate
from Fiche import Fiche
from Source import Source


def analyseFiche(nom_fichier, dossier, graph):
    with open(join(dossier, nom_fichier)) as f:
        content = f.readlines()
        content = [x.strip('\n') for x in content]
        fiche_contenu_list = []
        fiche_id = ''
        fiche_titre = ''
        fiche_contenu = ''
        fiche_date = ''
        fiche_auteur = ''
        fiche_references = ''
        for line in content:
            if line.startswith('fiche n°'):
                fiche_id = line.strip('fiche n°').strip()
            elif line.startswith('titre:'):
                fiche_titre = line.strip('titre:').strip()
            elif line.startswith('Références associées:'):
                fiche_references = line.strip('Références associées:').strip().split(' ')
            elif line.startswith('auteur:'):
                fiche_auteur = line.strip('auteur:').strip()
            elif line.startswith('date:'):
                fiche_date = line.strip('date:').strip()
            else:
                if line != '\n':
                    fiche_contenu_list.append(line)
        fiche_contenu = '\n'.join(fiche_contenu_list)
        fiche = Fiche(fiche_id, fiche_titre, fiche_auteur,
                      fiche_contenu, fiche_date, fiche_references)
        fiche.create_node(graph)
    return fiche


def ficheDocumentation(fiche, type_doc, dossier, nom_fichier, graph):
    with open(join(dossier, nom_fichier)) as ref_file:
        content = ref_file.readlines()
        content = [x.strip('\n') for x in content]
        for line in content:
            if (type_doc == "references"):
                ref_id, _, ref_leg = line.partition('@')
                if ref_id in fiche.get_references():
                    reference_trouvee = Source('Reference', ref_leg)
                    reference_trouvee.create_source(graph)
                    fiche.create_doc(graph, reference_trouvee, '')
            elif (type_doc == "images"):
                infos = line.split('@')
                fiche_id = infos[0]
                filename = infos[1]
                legende = infos[2]
                if fiche_id == fiche.get_tmp_id():
                    reference_trouvee = Source('Image', legende, filename)
                    reference_trouvee.create_source(graph)
                    fiche.create_doc(graph, reference_trouvee, '')


def main(project_directory, ignore_files):
    authenticate("localhost:7474", "neo4j", "haruspex")
    graph_db = Graph()
    dossier = os.path.join(project_directory + "/pages")

    if os.path.exists(dossier):
        # Pour chaque fiche, analyser son contenu
        # et créer les noeuds/liens correspondants
        files = [f for f in listdir(dossier) if isfile(join(dossier, f))]

        for fiche in files:
            if (fiche not in ignore_files):
                fiche_analysee = analyseFiche(fiche, dossier, graph_db)
                ficheDocumentation(fiche_analysee, "references", dossier,
                                   ignore_files[0], graph_db)
                ficheDocumentation(fiche_analysee, "images", dossier,
                                   ignore_files[1], graph_db)
    else:
        files = [f for f in listdir(project_directory) if (isfile(join(project_directory, f)) and f.endswith('.txt'))]
        #TODO récupérer les métadonnées d'omeka sur les documents
        for document in files:
            print(document.strip(project_directory))
            fiche = Fiche(document.replace(project_directory,'').replace('.txt', ''), '', '',
                          '', '', '')
            fiche.create_node(graph_db)

if __name__ == "__main__":
    project_directory = sys.argv[1]
    ignore_files = ["references", "images"]
    main(project_directory, ignore_files)
