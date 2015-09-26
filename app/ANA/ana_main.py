#!/usr/bin/env python3
# encoding: utf-8

import ana_useful
import ana_collect
import re
import sys
import os
import ntpath
import json
import ana_postprocessing


#config = json.loads(open(os.path.join(sys.argv[1],'ana_config.json')).read())
config = json.loads(open('/home/matthieu/MEGAsync/IRCCyN/projets/Haruspex/projet2/ana_config.json').read())

#FICHIERS D'ENTREE#####################################################
# linkwords_file_path = config['entries']['linkwords_file_path']
linkwords_file_path = config['linkwords_file_path']
stopword_file_path = config['stopword_file_path']
ana_useful.build_linklist(linkwords_file_path)
ana_useful.build_stoplist(stopword_file_path)

#FICHIERS A ANALYSER########################
abs_txt_file_path = config['txt_file_path']
path = os.path.dirname(os.path.realpath(abs_txt_file_path))
os.chdir(path)

txt_file_path = ntpath.basename(abs_txt_file_path)
bootstrap_file_path = config['bootstrap_file_path']

if not os.path.exists('output/'):
    os.makedirs('output/')
log_file_path = 'output/log'


# construire la liste cands à partir d'une recherche dans le dico des étiquettes et pas à partir du fichier bootstrap
with open(bootstrap_file_path, 'r', encoding = 'utf8') as bootstrapfile:
    cands = ana_useful.build_bootlist(bootstrapfile)
print('BOOTSTRAP : ',cands)

dict_occ_ref = ana_useful.text2occ(txt_file_path)

########################################################################


#SEUILS#################################################################
# nucleus_threshold = [3,5,5,10]
# nucleus_threshold = [2,4,4,6]
nucleus_threshold = config['nucleus_threshold']
expansion_threshold = int(config['expansion_threshold'])
expression_threshold = int(config['expression_threshold'])
recession_threshold = int(config['recession_threshold'])

#STEPS########################################################################
global_steps = int(config['global_steps'])
nucleus_steps = int(config['nucleus_nestedsteps'])
automaticsteps = config['automaticsteps'] # True ou False

with open(log_file_path, 'w', encoding = 'utf8') as logfile:
    ana_useful.write_log(log_file_path,"########################################\n")
    ana_useful.write_log(log_file_path,"FICHIER LOG\n")
    ana_useful.write_log(log_file_path,"ANALYSE DU FICHIER : " + txt_file_path + "\n")
    ana_useful.write_log(log_file_path,"BOOTSTRAP : " + str(cands) + "\n")
    ana_useful.write_log(log_file_path,"########################################\n")

stop = False
nb_passe = 0

while not stop:
    nb_passe += 1
    global_steps -= 1
    dict_expa = {}
    dict_expre = {}
    print('\n\n\n################# step n°', str(nb_passe), '#################\n')

    for nucleus_steps in range(1, nucleus_steps):
        ana_useful.write_log(log_file_path,"\n\n########################################\n")
        ana_useful.write_log(log_file_path, 'passe __ n°' + str(nb_passe) + " RECHERCHE DE NOYAUX\n")
        ana_useful.write_log(log_file_path,"########################################\n")
        dict_nucleus = ana_collect.nucleus_search(dict_occ_ref, cands, nucleus_threshold, log_file_path)
        ana_useful.conflict_manager(dict_occ_ref, dict_nucleus, dict_expa, dict_expre, recession_threshold, log_file_path)
        cands = ana_useful.recession(dict_occ_ref, recession_threshold, log_file_path)

    ana_useful.write_log(log_file_path,"\n\n########################################\n")
    ana_useful.write_log(log_file_path,'passe n°' + str(nb_passe) + " RECHERCHE D'EXPANSIONS\n")
    ana_useful.write_log(log_file_path,"########################################\n")
    dict_expa = ana_collect.expansion_search(dict_occ_ref, cands, expansion_threshold, log_file_path)

    ana_useful.write_log(log_file_path,"\n\n########################################\n")
    ana_useful.write_log(log_file_path,'passe n°' + str(nb_passe) + " RECHERCHE D'EXPRESSIONS\n")
    ana_useful.write_log(log_file_path,"########################################\n")
    dict_expre = ana_collect.expression_search(dict_occ_ref, cands, expression_threshold, log_file_path)

    ana_useful.write_log(log_file_path,"\n\n########################################\n")
    ana_useful.write_log(log_file_path,"\n\n########################################\n")
    ana_useful.write_log(log_file_path,'passe n°' + str(nb_passe) + " GESTION DE CONFLITS ET VALIDATION'\n")
    ana_useful.write_log(log_file_path,"########################################\n")
    ana_useful.conflict_manager(dict_occ_ref, dict_nucleus, dict_expa, dict_expre, recession_threshold, log_file_path)
    old_len_cands = len(cands)
    cands = ana_useful.recession(dict_occ_ref, recession_threshold, log_file_path)
    diff = len(cands)-old_len_cands
    print('Variation du nombre de candidats :', diff)
    print('CANDIDATS \n' , cands)

    if automaticsteps and diff == 0:
        automaticsteps = False #out ouf this loop next time, for 2 more rounds
        global_steps = 2 # run two more times  after having stoped discoverring cands.
    elif not automaticsteps and global_steps == 0:
        stop = True

ana_useful.write_output(cands, dict_occ_ref)
print('\n\n\n##################################################\n#################### END #########################\noutput files have been created in yourproject/output/ directory')
with open('output/dict_occ_ref.json', 'w') as json_dict_occ_ref:
    json.dump(dict_occ_ref, json_dict_occ_ref, ensure_ascii=False, indent=4)
