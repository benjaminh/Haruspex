#!/usr/bin/env python3
# encoding: utf-8
import useful
import objects


# en meta: il faut 1 dict pour les occurrences + 1 set pour les candidats
# ce sont nos 2 types d'objets typiques.

##########################
####### nucleus ##########
##########################
def nucleus_step(OCC, CAND, nucleus_threshold):
    #nucleus_threshold should be tuple formated like "vector" (see above)
    twords_dict = {}
    for cand in CAND:
        window = cand.nuc_window(OCC)# key:t_word_pos; value: (cand_id, link_word_type)
        twords_dict.update(window)

    twordsmerged = usefull.merge_egal_sple_dict(twords_dict)
    #key: shortest shape in soft_equality;
    #value dict{"equal_key":set of (occurrence_position), "equal_values": tuple of tuples(cand_id, link_word_type)}
    for case in twordsmerged:
        vector = usefull.count_nuc_cases(twordsmerged[case])
            #vector is tuple like this
            # s1: same linkword same CAND
            # s2: same linkword, different CAND
            # s3: different linkword, same CAND
            # s4: different linkword, different CAND
        if any[True for x in range(3) if vector[x] >= nucleus_threshold[x]]:
            next_id = len(CAND) + 1
            CAND[next_id] = Nucleus(idi = next_id, where = twordsmerged[case]["equal_key"], name = False, long_shape = case)#new CAND is created
            CAND[next_id].build(OCC)
    del twordsmerged#we don't need it anymore

##########################
###### Expression ########
##########################

def expression_step(OCC, CAND, expression_threshold, expansion_threshold):
    for cand in CAND:
        tword_inside, windowinside, window = cand.expre_window(OCC)
        # window{key :tuple(cand_id, nextcand_id); value: set of (tuple of occurrence_position)}
        # windowinside{key :tuple(cand_id, nextcand_id); value: set of (tword_inside_pos)}
        # tword_inside{key :tword_inside_pos; value: (tuple of occurrence_position)}
        for couple in window:
            expansions = set()
            if len(window[couple])<expression_threshold:#no need to look further, this will never become an expression
                continue#next couple in the loop
            if len(windowinside[couple]) >= expansion_threshold:#there may be an expa inside the expre!
                expansions = usefull.soft_equality_set(windowinside[couple], OCC, expansion_threshold)
                #expansions is a set of tuple containing the position of equals tword (len(tuple) >= expansion_threshold)
                #if expa then, there is an expansion inside, but there is maybe still enough occurrences to build expre and expa (later)
            if not expansions:#it is valid expression!
                CAND[next_id] = ...
            if expansions:#removing the future expansion inside windows
                occs_set = copy.copy(window[couple])#set of (tuple of occurrence_position) #cannot modify the dict in live and direct
                twords_pos = [item for expa in expansions for item in expa]#flattening the data; get the problematic twords_pos
                for tword_pos in twords_pos:
                    if occs_set.remove(tword_inside[tword_pos])
                if len(occs_set) >= expression_threshold:
                    valid_occ_set = occs_set
