#!/usr/bin/env python3
# encoding: utf-8
import ANA_useful
from ANA_extract import nucleus_step, exp_step, recession_step
import logging
import time
from os import chdir
from os.path import join, dirname, abspath
import json

Haruspexdir = dirname(abspath(__file__))
with open('workingdirectory', 'r') as dirfile:
    working_directory = join(dirfile.readline().rstrip(), 'ANA')
    chdir(working_directory)
# config = json.loads(open(os.path.join(sys.argv[1],'ana_config.json')).read())
config = json.loads(open(join(working_directory, 'ana_config.json')).read())
ANA_useful.setupfolder()# mkir  the useful sub-forlders
global_steps = int(config['global_steps'])
OCC, CAND, PAGES = ANA_useful.build_OCC(Haruspexdir, working_directory, config)
print('candidats trouvés à l\'amorce:', len(CAND))

#PROCESS CALL
stop = False
nb_passe = 0
old_len_diff = 0
while not stop:
    nb_passe += 1
    global_steps -= 1
    old_len_cands = len(CAND)
    for j in range(int(config['nucleus_nestedsteps'])):
        logging.info('\n### NUCLEUS ### step '+ str(nb_passe)+'.'+ str(j))
        nucleus_step(OCC, CAND, config)
    logging.info('\n### EXPANSION & EXPRESSION ### step '+ str(nb_passe))
    exp_step(OCC, CAND, config)
    logging.info('\n### RECESSION ### step '+ str(nb_passe) + '\n\n')
    recession_step(OCC, CAND, config)
    diff = len(CAND)-old_len_cands
    print('\n\n###### step '+ str(nb_passe))
    print('Nombre de candidats nouvellement trouvés :', diff)
    print('Nombre de candidats dont la taille a été modifiée', max(CAND) - len(CAND) - old_len_diff)
    old_len_diff = max(CAND) - len(CAND)
    #stop conditions:
    if config['automaticsteps'] and diff == 0:
        config['automaticsteps'] = False #out ouf this loop next time, for x more rounds
        if time.clock() < 15:#if it is a short process (less than xx sec)
            global_steps = 2#run 2 more times after having stoped discoverring cands. (-> building long xpre and xpa?)
        elif time.clock() < 200:
            global_steps = 1# run one more time after having stoped discoverring cands.
        else:
            stop = True
    elif global_steps == 0:
        stop = True

#WRITE OUTPUT
ANA_useful.write_output(CAND, OCC, PAGES, config)
