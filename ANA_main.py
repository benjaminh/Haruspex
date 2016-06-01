#!/usr/bin/env python3
# encoding: utf-8
import ANA_useful
import ANA_writeoutput
from ANA_extract import nucleus_step, exp_step, recession_step
import logging
import time
from os import chdir
from os.path import join, dirname, abspath
import yaml

Haruspexdir = dirname(abspath(__file__))
with open('workingdirectory', 'r') as dirfile:
    working_directory = join(dirfile.readline().rstrip(), 'ANA')
    chdir(working_directory)
# config = yaml.loads(open(os.path.join(sys.argv[1],'ana_config.yaml')).read())
config = yaml.load(open(join(working_directory, 'ana_config.yaml')).read())
config["started_at"]= time.time()#write it localy in the config dict
ANA_useful.setupfolder()# mkir  the useful sub-forlders
global_steps = int(config['steps']['global_steps'])
print('recherche de candidats à l\'amorce')
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
    for j in range(int(config['steps']['nucleus_nestedsteps'])):
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
    if config['steps']['automaticsteps'] and diff == 0:
        config['steps']['automaticsteps'] = False #out ouf this loop next time, for x more rounds
        if time.time() - t0 < 15:#if it is a short process (less than xx sec)
            global_steps = 2#run 2 more times after having stoped discoverring cands. (-> building long xpre and xpa?)
        elif time.time() - t0 < 200:
            global_steps = 1# run one more time after having stoped discoverring cands.
        else:
            stop = True
    elif global_steps == 0:
        stop = True

#WRITE OUTPUT
ANA_writeoutput.write(CAND, OCC, PAGES, config)
