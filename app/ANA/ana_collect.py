#!/usr/bin/env python3
# encoding: utf-8

import re
import ana_useful
from math import *

##################################################################
# EXPANSION
##################################################################

def expansion_valid_window(windows):
    valid_windows = []
    for window in windows:
        for occurrence in window:
            if ana_useful.is_cand(occurrence):
                pos_cand = window.index(occurrence)
        left_window = window[:pos_cand+1]
        right_window = window[pos_cand:]

        exists_linkword_R = ana_useful.exists_linkword(right_window)
        exists_linkword_L = ana_useful.exists_linkword(left_window)

        clean_window = ana_useful.window_wo_fword(window)
        #Les expansions ne doivent pas contenir de mot de schéma
        # Le CAND est forcément en position 2 par construction et suppression des mots v
        if clean_window[2][2] == 't' and not exists_linkword_R:
            valid_windows.append(window[pos_cand:])#RightWindow
        if clean_window[0][2] == 't' and not exists_linkword_L:
            valid_windows.append(window[:pos_cand+1])#LeftWindow
    return valid_windows

def expansion_cand_search(valid_windows, expansion_threshold):
    shape_list = []
    dict_cand_windows = {}
    for window in valid_windows:
        shape = ''
        for occurrence in window:
            if (occurrence[2] not in ['t','v']):
                shape += occurrence[2] + ' '
            if (occurrence[2] == 't'):
                shape += occurrence[1] + ' '
            shape.strip()
        dict_cand_windows.setdefault(shape,[]).append(window)
    print('\n\n\n################# RECHERCHE EXPANSIONS : DEBUT RECHERCHE CANDIDATS #################\n')
    # TODO Note : L'étape suivante est TRES longue
    dict_cand_windows_norm = ana_useful.merge_egal_sple_dictkeys(dict_cand_windows)
    print('\n\n\n################# RECHERCHE EXPANSIONS : FIN RECHERCHE CANDIDATS #################\n')

    # Vérification du dépassement de seuil, expansion est une "expansion potentielle" avant d'être validée et insérée dans le final_dict
    final_dict = {}
    for expansion in dict_cand_windows_norm:
        if ( (len(dict_cand_windows_norm[expansion])) >= expansion_threshold ):
            final_dict[expansion] = dict_cand_windows_norm[expansion]
    return final_dict


def expansion_search(dict_occ_ref, candidates, expansion_threshold, log_file_path):
    dict_expa = {}
    windows = ana_useful.define_windows(dict_occ_ref,candidates,3,2)
    valid_windows = expansion_valid_window(windows)
    dict_cand_windows = expansion_cand_search(valid_windows, expansion_threshold)

    # Find the new cand and build a new dict and write in the log, what there is at this step.
    for shape in dict_cand_windows:
        new_cand,occ_count = ana_useful.new_cand(dict_cand_windows[shape])
        ana_useful.write_log(log_file_path, 'EXPANSION TROUVEE ' + str(new_cand) + ' ' + str(occ_count))
        ana_useful.write_log(log_file_path, '   LISTE DES OCCURRENCES ')
        for window_cand in dict_cand_windows[shape]:
            ana_useful.write_log(log_file_path, '   ' + str(window_cand))
        # dict_expa.setdefault(new_cand,[]).append(dict_cand_windows[shape])
        dict_expa[new_cand] = dict_cand_windows[shape]
    return dict_expa


##################################################################
# EXPRESSION
##################################################################


#schema = [au, aux, d',de, du, des, en] pourquoi pas "avec"
#une fenetre valide ne contient que 2 CAND, séparés par un mot de schéma, avec éventuellement un mot 't' au milieu.

#windows are: (CAND1 + "aword" + CAND2)
# we check if the aword in center is not the same 3 times or more (this case it would be better to build an expansion first, then an expression)
def not_expa_inside_expre(windows):
    dict_awords_shape_seen = {}
    valid_windows_t3 = []
    awords_shapes_list = []

    for window in windows:
        aword_shape = ana_useful.aword_shape(window)
        dict_awords_shape_seen.setdefault(aword_shape, []).append(window) # the strict eguality (on the aword) is ok. But remains the eglité souple.

    dict_awords_shape = ana_useful.merge_egal_sple_dictkeys(dict_awords_shape_seen)

    if dict_awords_shape != {}:
        for aword_shape, windows in dict_awords_shape.items():
            if (0 < len(windows) < 3):
                valid_windows_t3.extend(windows)
    return valid_windows_t3

#schema = [au, aux, d',de, du, des, en] pourquoi pas "avec"
#une fenetre valide ne contient que 2 CAND, séparés par un mot de schéma, avec éventuellement un mot 't' au milieu.
def expression_valid_windows(windows, candidate):
    valid_window = []
    valid_windows = []
    buff = []

    for window in windows:
        if (ana_useful.exists_linkword(window) == True and ana_useful.count_cand(window) == 2):
            if ana_useful.is_cand(window[-1]): #list[-1] returns last item of the list
                cand2 = ana_useful.which_cand([window[-1]])
                if cand2[2] not in candidate.split(): #to avoid building expression like "bâtiment de cet ensemble de bâtiments" -> "batiment de bâtiment"
                    buff.append(window) #dans ce cas la fenetre valide est de type (CAND1 + "aword" + CAND2) avec un mot de schéma quelque part.
                # in the buffer because we need to know if the aword in center is not the same 3 times or more (this case it would be better to build an expansion first, then an expression)
            else:
                short_window = ana_useful.cut_window(window, 2)
                #Puisqu'on a 2 CAND et que la fenetre fait 3 mots et que le dernier mot n'est pas un CAND alors la fenetre était de type CAND + CAND + mot quelconque
                if ana_useful.exists_linkword(short_window) == True:
                    valid_windows.append(short_window) #dans ce cas la fenetre valide est de type (CAND1 + CAND2) avec un mot de schéma entre eux .

    # check if the aword in center is not the same 3 times or more (this case it would be better to build an expansion first, then an expression)
    valid_windows.extend(not_expa_inside_expre(buff))
    return valid_windows
##############

'''return a dict that looks like {shortshape: [valid_windows]}
shortshape is composed of two candidates concatenanted CANDCAND (no awords, no stopwords)'''
def expression_find_cand(valid_windows, expression_threshold):
    shortshape_list = []
    dict_cand_windows = {}
    i = 0
    for window in valid_windows:
        shortshape = ''
        #créer une shortshape pour chaque fenetre. une shortshape est 'CANDCAND'
        #apriori toutes les shortshapes commenceront par le même cand (celui en argument de la fonction `recherche_expression`)
        for occurrence in window:
            if ana_useful.is_cand(occurrence):
                shortshape += occurrence[2]
        shortshape_list.append(shortshape) # l'ordre des shortshapes dans shortshape_list conserve l'ordre des fenetres in valid_windows

    for shortshape in shortshape_list:
        occ_count = shortshape_list.count(shortshape)
        if occ_count >= expression_threshold:
            dict_cand_windows.setdefault(shortshape,[]).append(valid_windows[i])
        i += 1
    return dict_cand_windows


def expression_search(dict_occ_ref, candidates, expression_threshold, log_file_path):
    dict_expre = {}
    for candidate in candidates:
        candidate = [candidate] # in order to use the define_windows
        windows = ana_useful.define_windows(dict_occ_ref, candidate, 3, 1) #fenetre du type `CAND1 + (cand ou mot quelconque) + (cand ou mot quelconque)`. Les mots stop ("v") ne sont pas représentés
        valid_windows = []
        windows_cand_list = []

        valid_windows = expression_valid_windows(windows, candidate[0])

        if valid_windows != []:
            dict_cand_windows = expression_find_cand(valid_windows, expression_threshold)

            if dict_cand_windows != {}:
                for shortshape, windows_cand_list in dict_cand_windows.items():
                    new_cand, occ_count = ana_useful.new_cand_expression(windows_cand_list)
                    dict_expre[new_cand] = windows_cand_list
                    # dict_expre.setdefault(new_cand,[]).append(windows_cand_list)

                    ana_useful.write_log(log_file_path, 'EXPRESSION TROUVEE ' + str(new_cand) + ' ' + str(occ_count))
                    ana_useful.write_log(log_file_path, '   LISTE DES OCCURRENCES ')
                    for window_cand in windows_cand_list:
                        ana_useful.write_log(log_file_path, '   ' + str(window_cand))
    return dict_expre


##################################################################
# SIMPLE
##################################################################

#on cherche des mots rattachés à n'importe quel candidat par un mot de schéma. ex: couleurs de FLEUR, couleur de MUR, colleur de CARTON (c'est un exemple problematique)
# -> captera couleur.

#fait un dico de tous les mots trouvés (modulo une égalité souple)
def dict_found_words(valid_windows):
    dict_aword = {}
    # On ne peut pas modifier au fil de l'eau un dict sur lequel on itère
    # Donc on construit d'abord un dict avec tous les mots t
    # Peu importe s'ils sont égaux à l'égalité souple près

    for window in valid_windows:
        for occurrence in window: #a priori il n'y a qu'un seul t dans chaque fenetre'
            if occurrence[2] == 't':
                dict_aword.setdefault(occurrence[1],[]).append(window)
    final_dict = ana_useful.merge_egal_sple_dictkeys(dict_aword)
    return final_dict

def nucleus_find_cand(dict_aword, nucleus_threshold):
    dict_occ_cand = {}
    for shortshape, windows in dict_aword.items():
        count_s1 = 0 #Meme mot schema et même CAND
        count_s2 = 0 #Meme mot schema et CAND differents
        count_s3 = 0 #Mot schema different et même CAND
        count_s4 = 0 #Mot schema different et CAND different
        for window in windows:
            linkword = ana_useful.which_linkword(window)
            cand = ana_useful.which_cand(window)

            for window1 in windows:
                if window1 != window:
                    linkword1 = ana_useful.which_linkword(window1)
                    cand1 = ana_useful.which_cand(window1)
                    if linkword[1] == linkword1[1] and cand[2] == cand1[2]:
                        count_s1 += 1
                    elif linkword[1] == linkword1[1] and cand[2] != cand1[2]:
                        count_s2 += 1
                    elif linkword[1] != linkword1[1] and cand[2] == cand1[2]:
                        count_s3 += 1
                    elif linkword[1] != linkword1[1] and cand[2] != cand1[2]:
                        count_s4 += 1
        if count_s1/2 >= nucleus_threshold[0] or count_s2/2 >= nucleus_threshold[1] or count_s3/2 >= nucleus_threshold[2] or count_s4/2 >= nucleus_threshold[3]:
            for window in windows:
                for occurrence in window:
                    if occurrence[2] == 't':
                        dict_occ_cand.setdefault(shortshape, []).append(occurrence)
    return dict_occ_cand



#doit retourner la fenetre tronquée valide contenant un mot (non CAND) lié à un CAND par un mot schéma (après ce CAND) ou none si ne trouve rien.
def nucleus_valid_window(window):
    if ana_useful.exists_linkword(window):
        for occurrence in window:
            index_cand = 0
            if ana_useful.is_cand(occurrence):
                index_cand = window.index(occurrence)
                break
        right_window = window[index_cand:]
        if ana_useful.count_cand(right_window) < 2 and ana_useful.exists_linkword(right_window):
            return right_window

def nucleus_search(dict_occ_ref, candidates, nucleus_threshold, log_file_path):
    dict_nucleus = {}
    windows = ana_useful.define_windows(dict_occ_ref, candidates, 3, 2)
    valid_windows = []
    for window in windows:
        valid_window = nucleus_valid_window(window)
        if valid_window:
            valid_windows.append(valid_window)

        windowR = ana_useful.symmetric_window(window)
        valid_windowR = nucleus_valid_window(windowR)
        if valid_windowR:
            valid_window = ana_useful.symmetric_window(valid_windowR)
            valid_windows.append(valid_window)

    dict_aword = dict_found_words(valid_windows)
    dict_occ_cand = nucleus_find_cand(dict_aword, nucleus_threshold)

    if dict_occ_cand != {}:
        for shortshape, occ_cand_list in dict_occ_cand.items():
            new_cand, occ_count = ana_useful.new_cand_nucleus(occ_cand_list)
            dict_nucleus.setdefault(new_cand,[]).append(occ_cand_list)

            ana_useful.write_log(log_file_path, 'NOYAU TROUVE ' + str(new_cand) + ' ' + str(occ_count))
            # TODO retrouver les fenetres valides qui ont permis de créer le noyau
            ana_useful.write_log(log_file_path, '   LISTE DES OCCURRENCES')
            for occ_cand in occ_cand_list:
                ana_useful.write_log(log_file_path, '   ' + str(occ_cand))
    return dict_nucleus
