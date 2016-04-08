#!/usr/bin/env python3
# encoding: utf-8
import re
import logging
import ANA_useful
# from ANA_useful import str_simplify
import distance
# en meta: il faut 1 dict pour les occurrences + 1 set pour les candidats
# ce sont nos 2 types d'objets typiques.

Rconsonne = re.compile(r'[zrtypqsdfghjklmwxcvbn](?u)')

# global accent = {'é':'e', 'è', 'ê', 'ë', 'ù', 'û', 'ü', 'ç', 'ô', 'ö', 'œ', 'î', 'ï', 'â', 'à', 'ä']
# global wo_accent = ['e', 'e', 'e', 'e', 'u', 'u', 'u', 'c', 'o', 'o', 'oe', 'i', 'i', 'a', 'a', 'a']
SEUIL_EGAL_SPLE = 7

class Occurrence:
    def __init__(self, long_shape, cand = 0, cand_pos = set(), date = False, linkword = 0, tword = False, stopword = False):
        self.short_shape = ''#only to compare words
        self.long_shape = long_shape#keeping the long in a original utf8 format
        self.ascii_shape = ''# the long shape without accent and cédille
        self.cand = cand# an eventual reference to a cand_id
        self.cand_pos = cand_pos# set of neighbours that are part of the same cand
        self.date = date# is it a date?
        self.stopword = stopword# this pattern stops the construction of candidat ex: (. , : ! ...)
        # self.stopword = False #is it a stop word? USELESS
        self.linkword = linkword# or value by the line number in the schema file: [1:de, 2:du, 3:des, 4:d, 5:au, 6:aux, 7:en]
        self.tword = tword# is a normal_word?
        self.hist = []# the old references to the past cand states
        self.set_shapes()# build the shapes of the occ

    def set_cand(self, cand_id, cand_pos):
        old_cand = self._unlink()
        self.cand = cand_id# point to a new cand id
        self.cand_pos = cand_pos# get the new whole cand position it is part of
        return old_cand# is a tuple (old_cand_id, old_cand_pos)

    def _unlink(self):
        '''
        this function discard the tuple of occ_pos stored in the cand.where
        but  it does this for each occ of the canbd positions (not very efficient...)
        '''
        if self.cand:
            #TODO: old_pos trie plusieurs fois la même chose, (pour chaq occurrence lié au cand) -> pas très efficace
            old_pos = tuple(sorted(self.cand_pos))# need to copy in a (immutable) tuple to store that state (set are mutable)
            #"sorted to match the normal sorted form"
            old_cand = (self.cand, old_pos)
            self.hist.append(old_cand)# save the old reference to the cand
            return old_cand
        elif self.linkword:# a cand is not anymore a linkword nor anything
            self.hist.append(self.linkword)
            self.linkword = False
        elif self.tword:# a cand is not anymore a tword nor anything
            self.hist.append(self.tword)
            self.tword = False
        else:#is an empty_word
            self.hist.append('n')

    def _relink(self, CAND):
        if self.cand in CAND:# if the 'retored' cand still exists
            CAND[self.cand].where.add(self.cand_pos)
        else:#another recession...#TODO: think if there is a way to stop loop, in case of three cand branches recessing toghether to same root cand
            self._recession(CAND)

    def _recession(self, CAND):
        # if len(self.hist)==1:
        #     print(self.long_shape, self.cand, self.cand_pos, self.hist)
        if len(self.hist)>1:
            self.cand, self.cand_pos = self.hist.pop()# the initial state is stored as cand=0 in history
        else:# retrieve the initial state of the occ (not a CAND )
            self.cand = False
            self.cand_pos = set()
            state = self.hist.pop()
            if type(state)==bool:# it is a tword
                self.tword = True
            elif type(state)==int:# it is a linkword
                self.linkword = state
            elif state != 'n':# it is not an emptyword, it was a cand from the bootstrap
                self.cand, self.cand_pos = state
        if self.cand:
            self._relink(CAND)

    def set_shapes(self):
        if not self.date:
            self.ascii_shape = ANA_useful.str_simplify(self.long_shape)
            short_shape = [caract for caract in self.ascii_shape if (Rconsonne.match(caract))] #the 3 first charactere from the ascii shape
            short_shape = short_shape[:3]
            self.short_shape = ''.join(short_shape)
        else:
            self.ascii_shape = self.long_shape
            self.short_shape = self.long_shape

    def soft_equality(self, occ2):
        '''
        Prend 2 termes et retourne un booléen.
        Permet de définir si 2 termes sont égaux, en calculant une proximité entre eux.
        Un seuil de flexibilité est défini.
        ne tient pas compte des majuscules ni des accents.
        '''
        souple = False
        if self.short_shape == occ2.short_shape:
            if self.ascii_shape != '' and occ2.ascii_shape != '':
                if ((self.ascii_shape == occ2.ascii_shape) \
                or (occ2.ascii_shape == self.ascii_shape + 's') or (self.ascii_shape == occ2.ascii_shape + 's') \
                or (occ2.ascii_shape == self.ascii_shape + 'x') or (self.ascii_shape == occ2.ascii_shape + 'x') \
                or (occ2.ascii_shape == self.ascii_shape + 'e') or (self.ascii_shape == occ2.ascii_shape + 'e') \
                or (occ2.ascii_shape == self.ascii_shape + 'es') or (self.ascii_shape == occ2.ascii_shape + 'es')):
                    souple = True
                else:
                    totleng = len(self.ascii_shape) + len(occ2.ascii_shape)
                    dist = distance.levenshtein(self.ascii_shape, occ2.ascii_shape)
                    closeness = totleng / (SEUIL_EGAL_SPLE* dist)
                    if closeness > 1:
                        souple = True
        return souple




class Candidat:
    '''
    is pointed by the occurrences
    canot inherit from the occurrence class, because is composed by multiple occurrences, in a "standart form"
    '''

    def __init__(self, idi = 0, where = set()):
        self.id = idi
        self.where = where #set of tuple of occurrences positions. ex: ((15,16,17), (119,120,121), (185,186,187)) for long cands like expression
        self.whichpage = []
        logging.info('Cand '+ str(self.id) + ' created there: ' + str(self.where))
        # self.long_shape = long_shape # Normalized shape

    def nuc_window(self, OCC):#OCC is dict_occ_ref
        '''
        called from the all the cand instances,
        for new nucleus search based on all the cands,
        returns a dict with
            key :  tword_pos #unique no duplication
            value: (cand_id, link_word_type)
                #tuple are made of 2 things - caracterizing the occurrence
        '''
        found = {}

        for positions in self.where:#position is a tuple of occurrence positions for the cand. ex: ((15,16,17), (118,119,120,121), (185,186,187))
            cand_posmax = max(positions)#get the extrems tails of the cand position in the tuple. ex    17           121            187
            cand_posmin = min(positions)#get the extrems tails of the cand position in the tuple. ex    15           118            185
            linkword = 0
            tword_pos = None
            linkword_reverse = 0#on the other direction: matching the linkword backward (=before the cand)
            tword_reverse_pos = None#on the other direction: matching the tword backward (=before the cand)

            # in a first direction
            done = False
            i = 0
            while not done:
                i += 1
                try:
                    if OCC[cand_posmax+i].cand or OCC[cand_posmax+i].stopword: #need to be first: stop the while loop
                        break#faster than done=True
                    elif OCC[cand_posmax+i].linkword:
                        linkword = OCC[cand_posmax+i].linkword # get the id of the linkword
                    elif OCC[cand_posmax+i].tword:
                        if not linkword:
                            break#faster than done=True
                        else:
                            found[cand_posmax+i] = (linkword, self.id)# get the position of the t_word
                            done = True
                except KeyError:# means that the loop reached the end of the text
                    break

            # reversing the direction
            i = 0
            done = False
            while not done:
                i += 1
                try:
                    if cand_posmin-i<1:#avoid an infinite loop backward
                        break
                    if OCC[cand_posmin-i].cand or OCC[cand_posmin-i].stopword:
                        break#faster than done=True
                    elif OCC[cand_posmin-i].linkword:
                        linkword_reverse = OCC[cand_posmin-i].linkword # get the id of the linkword
                    elif OCC[cand_posmin-i].tword:
                        if not linkword_reverse:
                            break#faster than done=True
                        else:
                            found[cand_posmin-i] = (linkword_reverse, self.id)# get the position of the t_word
                            done = True
                except KeyError:# means that the loop reached the end of the text
                    break
        return found


    def expa_window(self, OCC):#OCC is dict_occ_ref
        '''
        called from the each of the cand instances,
        for expansion search based on each cand,
        returns a dict with
            key : tword_pos
            value: tuple(cand_position)
        '''
        found = {}

        for positions in self.where:#position is a tuple of occurrence positions for the cand. ex: ((15,16,17), (119,120,121), (185,186,187))
            done = False
            cand_posmax = max(positions)#get the extrems tails of the cand position in the tuple. ex    17           121            187
            i = 0
            while not done:
                i += 1
                try:
                    if OCC[cand_posmax+i].cand or OCC[cand_posmax+i].stopword:
                        break#faster than done=True
                    elif OCC[cand_posmax+i].linkword:#stops the while loop. if there is a linkword this shape is more likely to be a nucleus
                        break#faster than done=True
                    elif OCC[cand_posmax+i].tword:
                        found[cand_posmax+i] = positions
                        done = True
                except KeyError:# means that the loop reached the end of the text
                    break
        return found


    def expre_window(self, OCC):#OCC is dict_occ_ref
        '''
        called from the all the cand instances,
        for expression search based on all the cands,
        returns 2 dicts:
            # expre_where{tuple(cand_id, nextcand_id): set of tuples(cand_positions)}
            # expre_what{tuple(cand_positions): set of tuple(occ_pos of the potential expre)}
        '''

        expre_where = {}
        expre_what = {}

        for positions in self.where:#positions is a tuple of occurrence positions for the cand. ex: self.where = {(15,16,17), (119,120,121), (185,186,187)}
            cand_posmin = min(positions)
            cand_posmax = max(positions)#get the extrems tails of the cand position in the tuple. ex                17           121            187
            i = 0
            tword_inside_count = 0
            linkword = False
            while tword_inside_count<2 and i < 5:#limit on i to avoid connecting 2 cands separated by many emptywords
                i += 1
                try:
                    if OCC[cand_posmax+i].stopword:
                        break
                    # if OCC[cand_posmax+i].linkword:
                    #     linkword = True#FIXME why is it usefull to check for linkword??
                    elif OCC[cand_posmax+i].cand:# and linkword == True:
                        couple = (self.id, OCC[cand_posmax+i].cand)# tuple(cand_id, nextcand_id)
                        expre_pos = tuple(range(cand_posmin, max(OCC[cand_posmax+i].cand_pos)+1))# match till the the end tail of the next_cand; ()+1 is for the range behaviour)
                        expre_where.setdefault(couple, set()).add(positions)#add the set of position of the initial cand building the expre
                        expre_what[positions] = expre_pos
                        break
                    elif OCC[cand_posmax+i].tword:
                        tword_inside_count += 1
                except KeyError:# means that the loop reached the end of the text
                    break
        return expre_where, expre_what

    def _unlink(self, occurrences):#to remove the pointed occurrences in the where att of the cand
        #logging.info('Cand '+ str(self.id) + ' unlinked there: ' + str(occurrences))
        self.where.discard(occurrences)

    def recession(self, recession_threshold, OCC, CAND):
        if len(self.where) < recession_threshold:
            [OCC[position]._recession(CAND) for occurrences in self.where for position in occurrences]#remove the actual link to a cand in occ instance and replace it by the previous one
            return True#to destry the entry in the dict CAND from outside

    def destroy(self, cand_pos_to_discard, CAND, OCC):#cand_pos_to_discard is a dict{cand_id: set of tuple of occ_pos to be unlinked}
        for old_cand_id in cand_pos_to_discard:
            for old_cand_pos in cand_pos_to_discard[old_cand_id]:
                try:
                    CAND[old_cand_id]._unlink(old_cand_pos)
                except KeyError:
                    print('STRANGE')
                    print('not found', old_cand_id, old_cand_pos)
                    print('newcand', self.id)
                    print('newcand_pos', self.where)
                    for occ_pos in old_cand_pos:
                        print(OCC[occ_pos].long_shape, occ_pos)
                        print('cand_pos',OCC[occ_pos].cand_pos)
                        print('hist',OCC[occ_pos].hist)
                    print(OCC[max(old_cand_pos)+1].long_shape, max(old_cand_pos)+1)
                    print('cand_pos',OCC[max(old_cand_pos)+1].cand_pos)
                    print('hist',OCC[max(old_cand_pos)+1].hist)

    def build(self, OCC, CAND):
        cand_pos_to_discard = {}
        for cand_pos in self.where:#self.where is set of tuple of occurrences positions. ex: ((15,16,17), (119,120,121), (185,186,187)) for long cands
            new_pos = set(cand_pos)
            for occ_pos in cand_pos:
                old_cand = OCC[occ_pos].set_cand(self.id, new_pos)#get the position of the cand on theses occ (if any cand existed there)
                if old_cand:#in case of a nucleus no cand is to be discarded because is only a twords (does not imply cand growth), so oldcandid is None
                    old_cand_id, old_cand_pos = old_cand
                    cand_pos_to_discard.setdefault(old_cand_id, set()).add(old_cand_pos)
        self.destroy(cand_pos_to_discard, CAND, OCC)

    def merge(self, cands_idis, CAND):#list of cand_idi to merge with
        for cand_idi in cands_idis:
            self.where = self.where | CAND[cand_idi].where

class Nucleus(Candidat):
    '''
    on cherche des mots rattachés à n'importe quel candidat par un mot de schéma.
    ex: couleurs de FLEUR, couleur de MUR, colleur de CARTON (c'est un exemple problematique)
    -> captera couleur.
    '''

    def __init__(self, **kwargs):
        super(Nucleus, self).__init__(**kwargs)
        self.occ_represent = set()# this set contains one or several occ_pos, reprensenting all the different shape of the nuc.
        self.shape_represent = set()#this is a set of occ shape reprensenting all the different shape of the nuc. Not to rebuild the self.occ_represent set on each update

    def _representatives(self, OCC):
        shape_represent = set()
        for where in self.where:# where is a tuple of a single integer eg: (45,) -> where[0] get an occ_pos
            if OCC[where[0]].long_shape.lower() not in self.shape_represent:
                self.shape_represent.add(OCC[where[0]].long_shape.lower())
                self.occ_represent.add(where[0])

    def _update_representatives(self, occ_pos, OCC):
        if OCC[occ_pos].long_shape.lower() not in self.shape_represent:
            self.shape_represent.add(OCC[occ_pos].long_shape.lower())
            self.occ_represent.add(occ_pos)

    def _search_all_twords(self, OCC):
        for occ_pos in OCC:
            if OCC[occ_pos].tword:
                for occ_pos_repr in self.occ_represent:#try to match any of the shapes that allready matched
                    if (occ_pos,) not in self.where and OCC[occ_pos].soft_equality(OCC[occ_pos_repr]):# where is a tuple of a single integer eg: (45,) -> where[0] get an occ_pos
                        self.where.add((occ_pos,))#add the position (as a tuple of 1 integer) of the occurrence in soft equality
                        self._update_representatives(occ_pos, OCC)
                        break

    def buildnuc(self, OCC, CAND):
        self._representatives(OCC)
        self._search_all_twords(OCC)#search for all the occurrences of this new nucleus in the whole text
        return self.where, self.occ_represent, self.shape_represent

    def is_forbidden(self, forbidden_occinstance, OCC):
        '''run before writting results (at the end), theses cand may be used to build others, but not alone as a nucleus
        check if the nucleus is not one of the word that have no sense alone (ex: "supérieures" vs "études supérieures")
        forbidden_occinstance is only one instance of Occurence class, with a forbidden shape as long_shapeshape -> for soft eguality
        '''
        for occ_representant in self.occ_represent:
            if OCC[occ_representant].soft_equality(forbidden_occinstance):
                return True
        return False

class Page:
    def __init__(self, begin, idi):
        self.idi = idi
        self.where = (begin,)#tuple containaing the first and last occ indice of the page
        self.node = None
        self.what = []
