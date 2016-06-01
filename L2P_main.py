#!/usr/bin/env python3
# encoding: utf-8

from os import chdir
from os.path import join
import re
from L2P_indexing import writePages_and_txt4ana
from L2P_CleanLaTeX import cleanLatex
import yaml
from L2P_useful import setup_dir, convert_concat, concat_others
#config = yaml.loads(open(os.path.join(sys.argv[1],'L2P_config.yaml')).read())
# pour faire tourner en ligne de commande
with open('workingdirectory', 'r') as dirfile:
    working_directory = dirfile.readline().rstrip()
chdir(working_directory)
setup_dir()


config = yaml.load(open(join(working_directory, 'pages', 'L2P_config.yaml')).read())
writer2LaTeX_path = config['writer2LaTeX_path']

auteur = config['author']
date = config['publi_date']
write_lastsec = config['write_lastsection']# pour écrire ou non la conclusion...

##Options:
min_size = config['mini_size'] #taille minimum d'une section pour en 'extraire' une fiche (en nombre de mots)
parag_cut = config['paragraph_cut']  #mettre "True" pour considérer les paragraphes comme des subsubsubsection et en faire des fiches, ou bien mettre "False" pour les laisser dans des fiches mères
close_squarebrackets = config['close_squarebrackets'] #warning: in case of use of mathematics formula with non closed square bracket (eg: an range of values like [1976, 1986[) the folowing function will only produce problems!
#####################################



convert_concat(working_directory, writer2LaTeX_path)#convert and concatenate the odt and tex files into "concat.tex"
cleanLatex(working_directory, close_squarebrackets)#process "concat.tex"
concat_others(working_directory)#concatenate the raw text files to "concat.tex"
writePages_and_txt4ana(working_directory, write_lastsec, min_size, parag_cut ,auteur, date)
