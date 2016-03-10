#!/usr/bin/env python3
# encoding: utf-8
import ANA_useful
from ANA_extract import nucleus_step, exp_step, recession_step
import logging
import time
from os import chdir
from os.path import join, dirname, abspath
import json

with open('workingdirectory', 'r') as dirfile:
    working_directory = dirfile.readline().rstrip()


# config = json.loads(open(os.path.join(sys.argv[1],'ana_config.json')).read())
config = json.loads(open(join(working_directory,'ANA', 'ana_config.json')).read())

#GLOBAL LANG CONFIG
whereami = dirname(abspath(__file__))
stopwords_file_path = whereami + '/french/stopwords_fr.txt'#config['stopwords_file_path']
linkwords_file_path = whereami + '/french/schema'#config['linkwords_file_path']
emptywords_file_path = whereami + '/french/emptywords_fr.txt'#config['emptywords_file_path']


#####################
####LOCAL CONFIG#####
#####################
chdir(join(working_directory,'ANA'))
ANA_useful.setupfolder()# mkir  the useful sub-forlders

# TEXT
txt4ana =  config['txt4ana']
bootstrap_file_path = config['bootstrap']
extra_stopwords_file_path =  config['extra_stopwords']
extra_emptywords_file_path =  config['extra_emptywords']
match_propernouns = config['propernouns']

#SEUILS
nucleus_threshold = config['nucleus_threshold']
    #nuc threshold is tuple like this
    # s1: same linkword same CAND
    # s2: same linkword, different CAND
    # s3: different linkword, same CAND
    # s4: different linkword, different CAND
expansion_threshold = int(config['expansion_threshold'])
expression_threshold = int(config['expression_threshold'])
recession_threshold = int(config['recession_threshold'])

#STEPS
global_steps = int(config['global_steps'])
nucleus_steps = int(config['nucleus_nestedsteps'])
automaticsteps = config['automaticsteps'] # True ou False

#LOG INITIALIZE
logfilepath = join('log', 'ana.log')
logging.basicConfig(filename=logfilepath, format='%(levelname)s:%(message)s', level=logging.INFO)
starting = str(time.clock())
logging.info('Started at' + starting)

logging.info('### building the OCC dict ###')
OCC, CAND, PAGES = ANA_useful.build_OCC(txt4ana, stopwords_file_path, extra_stopwords_file_path, emptywords_file_path, extra_emptywords_file_path, linkwords_file_path, bootstrap_file_path, match_propernouns, working_directory)
print('candidats trouvés à l\'amorce:', len(CAND))

#PROCESS CALL
stop = False
nb_passe = 0
old_len_diff = 0
while not stop:
    nb_passe += 1
    global_steps -= 1
    old_len_cands = len(CAND)
    for j in range(nucleus_steps):
        logging.info('\n### NUCLEUS ### step '+ str(nb_passe)+'.'+ str(j))
        nucleus_step(OCC, CAND, nucleus_threshold)
    logging.info('\n### EXPANSION & EXPRESSION ### step '+ str(nb_passe))
    exp_step(OCC, CAND, expression_threshold, expansion_threshold)
    logging.info('\n### RECESSION ### step '+ str(nb_passe) + '\n\n')
    recession_step(OCC, CAND, recession_threshold)
    diff = len(CAND)-old_len_cands
    print('\n\n###### step '+ str(nb_passe))
    print('Nombre de candidats nouvellement trouvés :', diff)
    print('Nombre de candidats dont la taille a été modifiée', max(CAND) - len(CAND) - old_len_diff)
    old_len_diff = max(CAND) - len(CAND)
    #stop conditions:
    if automaticsteps and diff == 0:
        automaticsteps = False #out ouf this loop next time, for 2 more rounds
        if time.clock() < 30:#if it is a short process (less than 30 sec)
            global_steps = 2#run 2 more times after having stoped discoverring cands. (-> building long xpre and xpa?)
        elif time.clock() < 1000:
            global_step = 1# run one more time after having stoped discoverring cands.
        else:
            stop = True
    elif not automaticsteps and global_steps == 0:
        stop = True

#WRITE OUTPUT
print('candidats trouvés :', len(CAND))
ending = str(time.clock())
print('lasted: ', ending, ' seconds')
logging.info('Ended at' + ending)
ANA_useful.write_output(CAND, OCC, PAGES)
