#!/usr/bin/env python3
# encoding: utf-8

import json
import math
import os
import re
import distance
import copy
from collections import Counter

#paramètre globaux ou initialisation#############################
seuil_egal_sple = 8


#prend un fichier ligne à ligne et construit une liste avec un élément dans la liste pour chaque ligne
#file object est le produit de `open`
def build_bootlist(fileobject):
    global bootcands
    lines = fileobject.readlines()
    bootcands = list(map(lambda s: re.sub(r'\n', '', s), lines))
    return bootcands

def build_stoplist(stopword_file_path):
    global stopwords
    with open(stopword_file_path, 'r', encoding='utf8') as stopwordfile:
        lines = stopwordfile.readlines()
        stopwords = list(map(lambda s: re.sub(r'\n', '', s), lines))

def build_linklist(linkwords_file_path):
    global linkwords
    with open(linkwords_file_path, 'r', encoding = 'utf8') as linkwordsfile:
        lines = linkwordsfile.readlines()
        linkwords = list(map(lambda s: re.sub(r'\n', '', s), lines))

#ecrire log
def write_log(log_file_path, indication):
    with open(log_file_path, 'a', encoding = 'utf8') as logfile:
        logfile.write(indication + '\n')

#supprime l''accent de la première lettre du mot
#pas pour un problème d'encodage, mais pour un pb humain: les erreurs de "lettre non-accentué" en majuscule sont fréquentes. on veut : Île = Ile.
def accent_remove(lower_word):
    accent = ['é', 'è', 'ê', 'ë', 'ù', 'û', 'ü', 'ç', 'ô', 'ö', 'œ', 'î', 'ï', 'â', 'à', 'ä']
    wo_accent = ['e', 'e', 'e', 'e', 'u', 'u', 'u', 'c', 'o', 'o', 'oe', 'i', 'i', 'a', 'a', 'a']
    word = ''
    first_caracter = lower_word[0]
    lower_word2 = lower_word[1:]
    if first_caracter in accent:
        index = accent.index(first_caracter)
        first_caracter = first_caracter.replace(accent[index], wo_accent[index])
        if first_caracter in accent:
            print('ERREUR', first_caracter)
    word = first_caracter + lower_word2
    return word

# attention div#0 si word1 == word2
# utilisé pour egal_souple_term
def close(word1, word2):
    totleng = len(word1) + len(word2)
    dist = distance.levenshtein(word1, word2)
    closeness = totleng / (seuil_egal_sple* dist)
    return closeness

#Prend 2 termes et retourne un booléen. Permet de définir si 2 termes sont égaux, en calculant une proximité entre eux. Un seuil de flexibilité est défini. ne tient pas compte des majuscules mais des accent oui.
def egal_sple_term(word1, word2):
    souple = False
    if word1 != '' and word2 != '':
        word1 = accent_remove(word1.lower())
        word2 = accent_remove(word2.lower())
        if word2[0] != word1[0]:
            souple = False
        elif ((word1 == word2) or (word2 == word1 + 's') or (word1 == word2 + 's') or (word2 == word1 + 'e') or (word1 == word2 + 'e') or (word1 == word2 + 'es') or (word2 == word1 + 'es')):
            souple = True
        else:
            closeness = close(word1, word2)
            if closeness > 1:
                souple = True
    return souple

#Prend 2 chaînes et retourne un booléen. Permet de définir si 2 chaînes sont égales.
#Attention: ne supporte pas les stopwords dans les chaïnes.
#Calcul la sommes des proximités des paires de mots (chaine A, chaine B contiennent les paires A1 B1; A2 B2; A3 B3).
def egal_sple_chain(s1, s2):
#    st1 = re.sub(stopword_pattern, '', string1)
#    st2 = re.sub(stopword_pattern, '', string2)
    souple = False
    if ' '  in s1+s2:
        string1 = s1.split()
        string2 = s2.split()
        if len(string1) == len(string2):
            souple = True
            i = 0
            for word in string1:
                if not egal_sple_term(string2[i], word):
                    souple = False
                    break
                i += 1
    else:
        souple = egal_sple_term(s1, s2)
    return souple



# in dict_occ_ref, the keys are 'position' and the values are [shape, status, history]. str shape; str status; list of occurrence(s) history
def text2occ(txt_file_path):
    dict_occ_ref = {}
    i = 3
    dict_occ_ref[1] = ' ', 't', [] #fake first occurrence just to avoid having a cand in first position.
    with open(txt_file_path, 'r', encoding = 'utf8') as txtfile:
        text = txtfile.read()
        #texte = re.sub('-', '_', texte) # pour éviter de perdre les traits d'union '-'
        # separator = re.compile(r'\W+') #attention selon les distrib, W+ peut catcher les lettre accentuées comme des "non lettre"
        # words = re.split(separator, text)
        words = re.findall(r'(\w+[’|\']?|[.,!?;])(?siu)', text)
        for word in words:
            lower_word = word.lower()
            i += 1
            marked = False
            if (lower_word in stopwords) or re.match(r'wxcv[\d|_]*wxcv', word) or (re.match(r'(\b\d+\b)', word) and not re.match(r'(1\d\d\d|20\d\d)', word)): #les chiffres sont des 'v' mais pas les dates.:
                marked = True
                dict_occ_ref[i] = word, 'v', [] #the history is empty at the begining
            for cand in bootcands:
                egaux = egal_sple_term(cand, lower_word)
                if egaux == True:
                    marked = True
                    dict_occ_ref[i] = word, cand, [] #the history is empty at the begining
            if marked == False:
                dict_occ_ref[i] = word, 't', [] #the history is empty at the begining
        dict_occ_ref[i+1] = ' ', 't', [] #fake last occurrence just to avoid having a cand in last position.
        return dict_occ_ref


#prend en paramètres: le dico des étiquettes, une liste de `CAND`, `width` (taille de la fenetre) et `w` (position du `CAND` dans la fenêtre (1, 2, 3 ou 4 souvent)) et sort une liste de toutes les suites d'étiquettes numérotées (une fenetre) correspondant aux critères: les fenêtres. Les étiquettes sont de la shortshape [indice, mot, typemot] dans les fenetres.
def define_windows(dict_occ_ref, candidates, width, cand_pos):
    windows = []
    before_cand = cand_pos-1 # nombre d'étiquette avant le candidat dans la fenetre
    after_cand = width-cand_pos # nombre d'étiquette apres le candidat dans la fenetre
    for cand in candidates:
        for key, value in dict_occ_ref.items():
            window =[]
            if cand == value[1]: #trouve les étiquettes contenant candidat dans le dico
                #construit une window composée d'étiquettes
                window.append([key,value[0],value[1], value[2]]) #ajoute l'occurrence du candidat trouvé dans la fenetre
                count_bw = 0 # count forward steps
                count_fw = 0 # count backward steps
                key1 = key
                key2 = key
                # boucle pour insérer autant d'étiquettes que demandées (paramètres width et w) après le candidat (les stopwords (de type noté 'v') ne comptent pas)
                while count_fw < after_cand:
                    key1 +=1
                    if key1 in dict_occ_ref:
                        occurrence = [key1]
                        occurrence.extend(dict_occ_ref[key1])
                        window.append(occurrence) #insere les occurrence en fin de window. occurrence de la forme [indice, mot, typemot, history]
                        if occurrence[2] != 'v':
                            count_fw += 1
                # boucle pour insérer autant d'étiquettes que demandées (paramètres width et cand_pos) avant le candidat (les stopwords (de type noté 'v') ne comptent pas)
                while count_bw < before_cand:
                    key2 -=1
                    if key2 in dict_occ_ref:
                        occurrence = [key2]
                        occurrence.extend(dict_occ_ref[key2])
                        window.insert(0, occurrence) #insere les occurrence en début de window. occurrence de la forme [indice, mot, typemot, history]
                        if occurrence[2] != 'v':
                            count_bw += 1
                windows.append(window)  #met la window dans la liste des windows recherchées.
    return windows


#prend une window d'étiquette et supprime tout les mots de la stoplist contenu dans cette window. retourne une window_sans_v (sans linkwords)
#pas pour opérer mais pour faire des vérification de windows valides
def window_wo_fword(window):
    window_wo_fword = []
    for occurrence in window:
        if occurrence[2] != 'v':
            window_wo_fword.append(occurrence)
    return window_wo_fword

# Pour faire des calculs d'occurrence sans se préoccuper des indices
def window_wo_position(window):
    window_wo_pos = []
    for occ in window:
        window_wo_pos.append(occ[1:])
    return window_wo_pos

def symmetric_window(window):
    new_window = list(reversed(window))
    return new_window

def is_cand(occurrence):
    if occurrence[2] not in ['t', 'v']:
        return True
    else:
        return False

def count_cand(window):
    count_cand = 0
    for occurrence in window:
        if is_cand(occurrence):
            count_cand += 1
    return count_cand

def which_cand(window):
    for occurrence in window:
        if is_cand(occurrence):
            return occurrence

def exists_linkword(window):
    exists_linkword = False
    for occurrence in window:
        if occurrence[1] in linkwords:
            exists_linkword = True
    return exists_linkword

def which_linkword(window):
    for occurrence in window:
        if occurrence[1] in linkwords:
            return occurrence

# returns a list of a words in
def aword_shape(window):
    for occ in window:
        if occ[2] == 't':
            aword_shape = occ[1]
    return aword_shape



#prend une liste de window candidates et retourne un tuple [string, int] contenant le new_cand_shape et son occurence
#the new_cand_shape is CAND1 + last_linkword + CAND2.
def new_cand_expression(windows_cand_list):
    shapes =[]
    for window in windows_cand_list:
        shape_list = []
        for occurrence in window:
            if is_cand(occurrence):
                shape_list.append(occurrence[2])
            elif occurrence[1] in linkwords:
                link = occurrence[1] # récupère le denier linkword de la window
        shape = str(shape_list[0] + ' '+ link + ' ' + shape_list[1]) # CAND1 + last_linkword + CAND2.  ignore the awords, the stopwords...
        shapes.append(shape)
    new_cand = min(shapes, key=len).lower() # choose the shortest shape among the equivalent ones in windows_cand_list
    occ_count = len(windows_cand_list)
    return new_cand,occ_count #shortshape string et occurence de cette shortshape

def new_cand(windows_cand_list):
    shape_list = []
    for window in windows_cand_list:
        shape = ''
        for occurrence in window:
            if occurrence[2] not in ['v', 't']:
                shape += occurrence[2]
            else:
                shape += occurrence[1]
            shape += ' '
        shape_list.append(shape.strip())
    new_cand = min(shape_list, key=len).lower() # choose the shortest shape among the equivalent ones in windows_cand_list
    occ_count = len(windows_cand_list)
    return new_cand,occ_count

def new_cand_nucleus(occ_cand_list):
    shortshape_list = []
    for occurrence in occ_cand_list:
        shortshape_list.append(occurrence[1].strip())
    new_cand = min(shortshape_list, key=len).lower()
    occ_count = len(occ_cand_list)
    return new_cand,occ_count #shortshape string et occurence de cette shortshape

# tronque une fenetre après un certain nombre de mot non "v"
def cut_window(window, length):
    count = 0
    short_window = []
    for occurrence in window:
        if count < length:
            short_window.append(occurrence)
        if occurrence[2] != 'v':
            count += 1
        if count == length:
            break
    return short_window

def write_output(cands, dict_occ_ref):
    # with open('output/context.txt', 'w', encoding = 'utf8') as contextfile:
        with open('output/keywords.txt', 'w', encoding = 'utf8') as outputfile:
                dict_output = {}
                dict_context = {}
                # contextfile.write("file for corrrelating the found candidates in their original context")
                for cand in cands:
                    dict_occ_ref[-4] = '', 't', []
                    dict_occ_ref[-3] = '', 't', []
                    dict_occ_ref[-2] = '', 't', []
                    dict_occ_ref[-1] = '', 't', []
                    dict_occ_ref[0] = '', 't', [] #The firs key was 1; 0 is a fake first occurrence to be able to write the context of an eventual first occurrence cand
                    windows = define_windows(dict_occ_ref, [cand], 9, 5)
                    dict_output[cand] = len(windows) # number of occurrences found (how many context windows)
                    for window in windows:
                        contextstr = ''
                        for occ in window:
                            if re.match(r'wxcv', occ[1]):
                                continue
                            else:
                                contextstr += (occ[1] + ' ') #re-create the 'lost spaces'
                        # contextfile.write(str(contextstr)+'\n')
                        contextstr = re.sub(r'( )(?=[\.,:!?])', '', contextstr) # delete the spaces followed by any ponctuation.
                        contextstr = re.sub(r'(?<=\'|’)( )', '', contextstr) # delete the spaces ater an apostrophe
                        dict_context.setdefault(cand, []).append(str(contextstr)) #create a dict of each cand's context to drop in a json file for the GUI
                with open('output/context.json', 'w') as json_contextfile:
                    json.dump(dict_context, json_contextfile, ensure_ascii=False, indent=4)
                outputfile.write("keywords and occurrences\n\n")
                cands_ordered = sorted(dict_output, key=lambda cand: dict_output[cand], reverse=True)
                for key in cands_ordered:
                    outputfile.write(str(dict_output[key]) + ' :  ' + str(key) + '\n')

def merge_dicts(dict_list):
    result = {}
    for dictionary in dict_list:
        result.update(dictionary)
    return result

def merge_egal_sple_dictkeys(*dict_args):
    '''
    the dicts should be with str type as key,
    based on egal_sple fonction.
    the new key gathering all the merged keys (found in sple_egal) wil be the most occurring one.
    Given any number of dicts, shallow copy and merge into a new dict,
    based on egal_sple fonction.
    '''
    if len(dict_args) > 1:
        merged = merge_dicts(dict_args)
    else:
        merged = dict_args[0]

    if len(merged) == 1: # faster if there is only one pair of (key, value) in the dict!
        return merged
    else:
        ordered_keys = sorted(merged, key=lambda clef: len(merged[clef]), reverse=True)
        z = {}
        seen = []
        for key1 in ordered_keys:
            for key2 in ordered_keys:
                if (egal_sple_chain(key1, key2) and key2 not in seen):
                    z.setdefault(key1, []).extend(merged[key2])  # concatenate the value of the the egal keys
                    seen.append(key2)
        return z

#get all the original positions of the occurences in a window
def get_pos(window):
    positions_list = []
    for occurrence in window:
        positions_list.append(occurrence[0])
    return positions_list

#sould return a list of all the occurrences (nucleuses) corresponding to the asked 'cand_shape'.
#doit servir la construction du dico des nucleus
def where_R_nucleus(dict_occ_ref, cand_shape):
    occ_list = []
    for position, value in dict_occ_ref.items():
        if ((value[1] == 't') and (egal_sple_term(value[0], cand_shape))): # Test on 't' word to avoid catching 'v' words (ie. 'il') for a candidate (ie. 'île')
            occurence = [position, value[0], value[1], value[2]]
            occ_list.append(occurence)
    return occ_list


def recession(dict_occ_ref, threshold, log_file_path):
    cands = []
    dict_cand = {}
#1. build a dico, to count the occurrences of each candidate.
    for position, value in dict_occ_ref.items():
        if value[1] not in ['v', 't']:
            dict_cand.setdefault(value[1],[]).append(position) # ajoute la position de chaque forme candidate trouvé dans un dico, à la clef "candidat"
#2. check if metting ends of differents cands is possible


#2. check if cand is still occuring in the dict_occ_ref
    for candidate, position_list in dict_cand.items():

        if len(position_list) >= threshold:
            cands.append(candidate)
        else: #supprime ce CAND et redécompose en occurrence ancienne grace à history
            for position in position_list:
                #recupère le texte contenu dans cette etiquette CAND à supprimer
                last_history = dict_occ_ref[position][2] #returns last state of the candidate from its history. last_histoy is a window of occurrences or a window of a single occurrence in case of a nucleus.
                for occurrence in last_history:
                    replace_pos = occurrence[0]
                    replace_val = occurrence[1:]
                    dict_occ_ref[replace_pos] = replace_val
                write_log(log_file_path, 'RECESSION de ' + str(candidate) + ' (' + str(position) + ') ' + ' vers ' + str(last_history))
    return cands


def admission(dict_occ_ref, window, new_cand_shape, log_file_path):
    '''
    new_cand est une chaîne de caractères normalisée en fonction des cas:
    - expression
    - expansion
    - simple
    It only modifies one window (= works window per window = doesn't accept a list of windows)
    '''
    shapes_list = []
    new_history = []    # in case of a nucleus, the var window is actualy an occurrence
    if isinstance(window[0], int):
        occurrence = window
        # in dict_occ_ref, the keys are 'position' and the values are [shape, status, history]. str shape; str status; list of window history
        history = occurrence[3] # catch the history of the occurrence that will be modify
        hist_to_add = copy.deepcopy(occurrence)
        history.append(hist_to_add)
        dict_occ_ref[occurrence[0]] = occurrence[1], new_cand_shape, history #history is in brackets cause it should be same format as a window.
        write_log(log_file_path, "NUCLEUS CHANGÉ " + str(dict_occ_ref[occurrence[0]]))

    # in case of an expression, or expansion
    else:
        window.sort(key=lambda x: x[0]) #trie les occurrences de la window par ordre d'indice croissant . au cas où

        occurrence1 = window[0]
        new_position = occurrence1[0]
        new_history = []
        if new_position in dict_occ_ref: # sinon une opération de change etiquette a déjà été effectuée pendant cette passe à cet indice.
            for occurrence in window:
                shapes_list.append(occurrence[1]) # catch the shapes of each occurrence concerned
                hist_to_add = copy.deepcopy(occurrence) # catch the history of the occurrences concerned
                new_history.append(hist_to_add)
            new_shape = ' '.join(shapes_list)
            dict_occ_ref[new_position] = new_shape, new_cand_shape, new_history # remplace la première étiquette de la window (en arg) par le new_string, le new_cand et update history
            for occurrence in window[1:]:
                position = occurrence[0] # get the keys of the occ to delete
                try:
                    del dict_occ_ref[position] # supprime les autres indices dans le dict_occ_ref
                except:
                    print ('  OCCURRENCE NON TROUVÉE, donc non supprimée: base: '+ str(window[0]) + ' avec: '+ str(occurrence))
            write_log(log_file_path, '  OCCURRENCE RE-COMBINÉE : ' + str(occurrence) +'vers ' + str(dict_occ_ref[new_position]))



'''
les dict_expa, dict_expre, dict_nucleus doivent être de la forme suivant: {new_cand:[occurences]}
le dict des nucleus doit peut-être être traité à part, et avant les autres pour favoriser l'exploration du texte.
'''
def conflict_manager(dict_occ_ref, dict_nucleus, dict_expa, dict_expre, threshold, log_file_path):
    seen = []
    tampon = []
##### for the nucleuses
    # 1: building the dict containing all the occurences to modify in the dict_occ_ref
    if dict_nucleus != {}:
        all_nucleus_dict = {}
        for new_cand_shape in dict_nucleus:
            occ_list = where_R_nucleus(dict_occ_ref, new_cand_shape)
            all_nucleus_dict[new_cand_shape] = occ_list
        # 2: modify by most occuring form
        #sort the dictionary in a tuple (cand shape, [occ_list]), in which the first item contain the most occuring cand_shape.
        #NB: the nucleuses are composed by a unique word, so a unique occurence, so there are no "windows" but only opccurences
        all_nucleus_ordered = sorted(all_nucleus_dict, key=lambda new_cand_shape: len(all_nucleus_dict[new_cand_shape]), reverse=True)
        for new_cand_shape in all_nucleus_ordered:
            occurrences = all_nucleus_dict[new_cand_shape]
            if len(occurrences) > (threshold-1):
                for occ in occurrences:
                    # if occ[0] not in seen:
                    #     seen.append(occ[0])
                    admission(dict_occ_ref, occ, new_cand_shape, log_file_path)
                write_log(log_file_path, 'NUCLEUS ADMIS ' + str(new_cand_shape) + ' ' + str(len(occurrences)))


##### for the other new_cands
    if dict_expa != {} or dict_expre != {}:
        all_cands_dict = merge_egal_sple_dictkeys(dict_expa, dict_expre)

        tampon = []
        #trie le dictionnaire en un tuple (cand shape, [occ_list]) dont le premier item contient le cand_shape ayant le plus d'occurences
        all_candshape_ordered = sorted(all_cands_dict, key=lambda new_cand_shape: len(all_cands_dict[new_cand_shape]), reverse=True)
        for new_cand_shape in all_candshape_ordered:
            windows = all_cands_dict[new_cand_shape]
            if len(windows) >= threshold:
                passed = False #to know if the new_cand has been accepted
                seen_buff = [] #to count the number of accepted occurrences (not in conflict with a previous one)
                buff = []
                occ_count = threshold #initialized with the smallest possible. THe count begin when the threshold is crossed
                for window in windows:
                    pos_list = get_pos(window)
                    deja_vu =  any((True for x in pos_list if x in seen)) # doesn't enter in the loop if one of the position has allready be seen this step.
                    if not deja_vu:
                        if passed: # passed if true only if there are more than 3 elements to modify
                            seen.extend(pos_list)
                            admission(dict_occ_ref, window, new_cand_shape, log_file_path)
                            occ_count += 1
                        else: # until there are 3 elements to modify
                            buff.append(window)
                            seen_buff.extend(pos_list)
                            if len(buff) == threshold: #  where there are 3 elements t modify (threshold crossed)
                                seen.extend(seen_buff)
                                for window in buff: # admission only accepts one window
                                    admission(dict_occ_ref, window, new_cand_shape, log_file_path)
                                passed = True
                if passed:
                    write_log(log_file_path, 'CANDIDAT ADMIS ' + str(new_cand_shape) + ' ' + str(occ_count))


#
#
#
#
#
