#!/usr/bin/env python3
# encoding: utf-8
import ANA_useful
from ANA_Objects import Nucleus, Candidat, Occurrence

# en meta: il faut 1 dict pour les occurrences + 1 set pour les candidats
# ce sont nos 2 types d'objets typiques.

##########################
####### nucleus ##########
##########################
def nucleus_step(OCC, CAND, config):
    newnucs_idis = []
    #nucleus_threshold should be tuple formated like "vector" (see above)
    twords_dict = {}
    for cand in CAND:
        window = CAND[cand].nuc_window(OCC)# key:t_word_pos; value: (link_word_type, cand_id)
        twords_dict.update(window)
    twordsmerged = ANA_useful.merge_egal_sple_dict(OCC,twords_dict)
    #twordsmerged {key: tuple of (twords_position); value: list of tuples(link_word_type, cand_id)}
    for case in twordsmerged:
        if len(twordsmerged[case]) > min(config['extract']['nucleus_threshold']):
            vector = ANA_useful.count_nuc_cases(twordsmerged[case])
                #vector is tuple like this
                # s1: same linkword same CAND
                # s2: same linkword, different CAND
                # s3: different linkword, same CAND
                # s4: different linkword, different CAND
            if any([True for x in range(4) if vector[x] >= config['extract']['nucleus_threshold'][x]]):
                next_id = max(CAND) + 1
                positions = set([tuple([position]) for position in case]) #we want a set of tuple of position presented like this set([(1,), (3,), (6,)])
                CAND[next_id] = Nucleus(idi = next_id, where = positions)#new CAND is created
                newnucs_idis.append(next_id)
    ANA_useful.dispatch_buildnuc(newnucs_idis, CAND, OCC)

##########################
###### expression ########
########## and ###########
###### expansion #########
##########################

def exp_step(OCC, CAND, config):
    CAND2build = {}# storing the CAND to be created while looping in the dict
    done = set()# to avoid expre conflicts for cases like A de B de C -> A de B and B de C exist; we have to choose!
    forbid = set()#set of occ positions allready "seen"
    exprewin = {}
    valid_exprewin = {}
    expression_threshold = int(config['extract']['expression_threshold'])
    expansion_threshold = int(config['extract']['expansion_threshold'])
    for cand_id in CAND:
        expawin = CAND[cand_id].expa_window(OCC)# {t_word_pos: tuple_cand_positions)
        expre_where, expre_what = CAND[cand_id].expre_window(OCC)
        # expre_where{tuple(cand_id, nextcand_id): set of tuples(firstcand_positions)}
        # expre_what{tuple(firstcand_positions): tuple(occ_pos of the ptential expre)}
        ########conflict management #first: check for forbidden positions, because valid expa
        expawinmerged = ANA_useful.merge_egal_sple_dict(OCC, expawin)# {tuple(t_word_pos):list of (tuple_cand_positions)}
        if expawinmerged:
            for expa_twords_eq in expawinmerged:
                if len(expa_twords_eq) >= expansion_threshold:
                    # forbid = set(tuple_cand_positions)
                    #Build the cand expa (inside or not) by the way...
                    where = set()#where is set of tuple of expa_positions
                    for valid_tword in expa_twords_eq:#for each item of the key (key is a tuple) = for t_word in the tuple of equivalent t_words
                        expa_area = tuple(range(min(expawin[valid_tword]),valid_tword+1))# tuple = expa occ_positions = all lintegers between min of the cand positions and tword position (+1 for range method behaviour)
                        #print('expaarea', expa_area)
                        where.add(expa_area)
                        forbid.update(set(expa_area))
                    next_id = max(CAND) + 1 + len(CAND2build)
                    CAND2build[next_id] = (next_id, where)# new CAND to be created (stored while looping in the dict)
        #second: remove the allready  position from the expre_windows and build exprewindow dict (clean one)
        if expre_where:
            for couple in sorted(expre_where, key=lambda couple: len(expre_where[couple])):#the less occuring expre first
                if len(expre_where[couple]) >= expression_threshold:# set of tuples(firstcand_positions). the shorter, not long enough are rejected
                    for cand_positions in expre_where[couple]:#for each tuple of cand_positions
                        expre_area = expre_what[cand_positions]#tuple, all occ positions between the head of firstcand_positions and the extrem tail of second cand position
                        #print('exprearea',expre_area)
                        if not forbid & set(expre_area):#no intersection: none of the expre_pos is forbiden (allready seen by the expa)
                            exprewin.setdefault(couple, set()).add(expre_area)#retrieve the whole expre pos from the single first cand_pos
                            #expre_what[couple] is a set of tuple(occ_pos of the entire expre) -> spread over 2 cands and the inbetween -> contain the future cand.where
            #third : building the new expre, starting with the less occurring ones.
            # Managing conflicts for cases like A de B de C -> A de B and B de C exist; we have to choose!
    if config['extract']['short_expre_before']:
        sortedexp = sorted(exprewin, key=lambda couple: len(exprewin[couple]))
    else:
        sortedexp = sorted(exprewin, key=lambda couple: len(exprewin[couple]), reverse=True)
    for couple in sortedexp:
        if len(exprewin[couple]) >= expression_threshold:
            for expre_area in exprewin[couple]:
                if not forbid & set(expre_area):
                    forbid.update(set(expre_area))
                    valid_exprewin.setdefault(couple, set()).add(expre_area)
    for couple in valid_exprewin:
        next_id = max(CAND) + 1 + len(CAND2build)
        CAND2build[next_id] = (next_id, valid_exprewin[couple])# new CAND to be created (stored while looping in the dict)
    for idi, value in CAND2build.items():#building all the new cands
        CAND[idi] = Candidat(idi = value[0], where = value[1])
        CAND[idi].build(OCC, CAND)

##########################
####### recession#########
##########################

def recession_step(OCC, CAND, config):
    recession_threshold = int(config['extract']['recession_threshold'])
    todel = set()
    for idi in CAND:
        if CAND[idi].recession(recession_threshold, OCC, CAND):
            todel.add(idi)
    for idi in todel:
        del CAND[idi]
