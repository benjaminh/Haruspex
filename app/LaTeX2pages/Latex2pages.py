#!/usr/bin/env python3
# encoding: utf-8

import os, sys
import re
import indexing
import CleanLaTeX
import json
config = json.loads(open(os.path.join(sys.argv[1],'L2P_config.json')).read())
# pour faire tourner en ligne de commande
# config = json.loads(open('L2P_config.json').read())
etape = 1

Fichier_a_traiter = config['texfile_path']
path = os.path.dirname(os.path.realpath(Fichier_a_traiter))
os.chdir(path)

Auteur_du_document = config['author']
Date_de_publication_du_document = config['publi_date']
DossierImage = config['pict_folder'] # écrire 'automatic' si le LaTeX provient de Writer2Latex. Sinon mettre le nom du dossier où sont rangées les images.
Mot_apres_la_derniere_fiche = config['last_word']# pour écrire et arréter l'écriture de la dernière partie avant la conclusion...

##Options:
Taille_minimale = config['mini_size'] #taille minimum d'une section pour en 'extraire' une fiche (en nombre de mots)
decoupe_paragraphe = config['paragraph_cut']  #mettre "True" pour considérer les paragraphes comme des subsubsubsection et en faire des fiches, ou bien mettre "False" pour les laisser dans des fiches mères
close_squarebrackets = config['close_squarebrackets'] #warning: in case of use of mathematics formula with non closed square bracket (eg: an range of values like [1976, 1986[) the folowing function will only produce problems!
#####################################

if not os.path.exists('BeingClean/'):
	os.makedirs('BeingClean/')
if not os.path.exists('pages/'):
	os.makedirs('pages/')



etape += CleanLaTeX.AcoladeClose(Fichier_a_traiter, etape)
if close_squarebrackets:
	etape += CleanLaTeX.CrochetClose(Fichier_a_traiter, etape)
etape += CleanLaTeX.Clean(Fichier_a_traiter, etape)
indexing.writePages_and_txt4ana(Fichier_a_traiter, Mot_apres_la_derniere_fiche, Taille_minimale, etape, decoupe_paragraphe, Auteur_du_document, Date_de_publication_du_document, DossierImage)
print('\n\n\n##################################################\n#################### END #########################\noutput files have been created in yourproject/output/ directory')
