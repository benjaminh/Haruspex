#!/usr/bin/env python3
# encoding: utf-8

# en meta: il faut 1 dict pour les occurrences + 1 set pour les candidats
# ce sont nos 2 types d'objets typiques.

Rconsonne = re.compile(r'[zrtypqsdfghjklmwxcvbn](?u)')
global rm_accent = {'é':'e', 'è':'e', 'ê':'e', 'ë':'e', 'ù':'u', 'û':'u', 'ü':'u',
    'ç':'c', 'ô':'o', 'ö':'o', 'œ':'oe', 'î':'i', 'ï':'i', 'â':'a', 'à':'a', 'ä':'a'}
# global accent = {'é':'e', 'è', 'ê', 'ë', 'ù', 'û', 'ü', 'ç', 'ô', 'ö', 'œ', 'î', 'ï', 'â', 'à', 'ä']
# global wo_accent = ['e', 'e', 'e', 'e', 'u', 'u', 'u', 'c', 'o', 'o', 'oe', 'i', 'i', 'a', 'a', 'a']
SEUIL_EGAL_SPLE = 7

class Occurrence:
    def __init__(self):
        self.short_shape = '' #only to compare words
        self.long_shape = '' #keeping the long in a original utf8 format
        self.ascii_shape = '' # the long shape without accent and cédille
        self.cand = 0 #an eventual reference to a cand_id
        self.date = False #is it a date?
        self.stopword = False #is it a stop word?
        self.linkword = 0 # or value by the line number in the schema file: [1:de, 2:du, 3:des, 4:d, 5:au, 6:aux, 7:en]
        self.tword = False # is a normal_word?
        self.hist = [] # the old references to the past cand states

    def set_cand(self, cand_id):
        old_cand = self.cand
        self.hist.append(old_cand)# save the old reference to the cand
        self.cand = cand_id# point to a new cand id
        return old_cand# to remove the inverse pointing reference in the cand obj

    def set_shapes(self):
        if not self.date:
            # self.set_ascii_longshape()
            self.ascii_shape = [rm_accent[caract] for caract in self.long_shape.lower() if caract in rm_accent] #if charac in the dict of accentuated charact, then replace it by its non-accentuated match
            self.ascii_shape = ''.join(ascii_shape)
            self.short_shape = [caract for caract in self.ascii_shape if (Rconsonne.match(caract) and len(short_shape)<4)] #the 3 first charactere from the ascii shape
            self.short_shape = ''.join(short_shape)

    def recession(self):
        self.cand = self.hist.pop()# the initial state is stored as cand=0 in history

    def soft_eguality(self, occ2):
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

    def __init__(self, idi = 0, where = set(), name = False, long_shape = ''):
        self.id = idi
        self.where = where #set of tuple of occurrences positions. ex: ((15,16,17), (119,120,121), (185,186,187)) for long cands like expression
        self.name = name # is it a propernoun: a place, a personn... (begin with a uppercase)
        self.long_shape = long_shape


    def nuc_window(self, OCC):#OCC is dict_occ_ref
        '''
        called from the all the cand instances,
        for new nucleus search based on all the cands,
        returns a dict with
            key :  tword_pos #unique no duplication
            value: (cand_id, link_word_type)
                #tuple are made of 2 things - caracterizing the occurrence
        '''
    #TODO travailler sur les différences entre linkword (ex: de la VS de...?)
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
                if OCC[cand_posmax+i].cand: #need to be first: stop the while loop, also no cand (ex t_word) will match even if t_word is still True...
                    break#faster than done=True
                elif OCC[cand_posmax+i].linkword:
                    linkword = OCC[cand_posmax+i].linkword # get the id of the linkword
                elif OCC[cand_posmax+i].tword:
                    if not linkword:
                        break#faster than done=True
                    else:
                        found[cand_posmax+i] = (linkword, self.id)# get the position of the t_word
                        done = True

            # reversing the direction
            i = 0
            done = False
            while not done
                i += 1
                if OCC[cand_posmin-i].cand: # more robust if first: no cand (ex t_word) will match even if t_word is still True...
                    break#faster than done=True
                elif OCC[cand_posmin-i].linkword:
                    linkword_reverse = OCC[cand_posmin-i].linkword # get the id of the linkword
                elif OCC[cand_posmin-i].tword:
                    if not linkword_reverse:
                        break#faster than done=True
                    else:
                        found[cand_posmin-i] = (linkword_reverse, self.id)# get the position of the t_word
                        done = True
        return found


    def expa_window(self, OCC):#OCC is dict_occ_ref
        '''
        called from the all the cand instances,
        for expansion search based on all the cands,
        returns a dict with
            key :  cand_id
            value: set of tword_pos
        '''
        found = {}

        for positions in self.where:#position is a tuple of occurrence positions for the cand. ex: ((15,16,17), (119,120,121), (185,186,187))
            done = False
            cand_posmax = max(positions)#get the extrems tails of the cand position in the tuple. ex    17           121            187
            i = 0
            while not done:
                i += 1
                if OCC[cand_posmax+i].cand: #need to be first: stop the while loop, also no cand (ex t_word) will match even if t_word is still True...
                    break#faster than done=True
                elif OCC[cand_posmax+i].linkword: #stops the while loop. if there is a linkword this shape is more likely to be a nucleus
                    break#faster than done=True
                elif OCC[cand_posmax+i].tword:
                    found.setdefault(self.id, set()).add(cand_posmax+i)
                    done = True
        return found


    def expre_window(self, OCC):#OCC is dict_occ_ref
        '''
        called from the all the cand instances,
        for expression search based on all the cands,
        returns a dict with
            {key :  tuple(cand_id, nextcand_id)
            value: set of (tuple of occurrence_position)}
        '''

        found = {}

        for positions in self.where:#position is a tuple of occurrence positions for the cand. ex: ((15,16,17), (119,120,121), (185,186,187))
            done = False
            tword_inside_pos = None
            cand_posmin = min(positions)
            cand_posmax = max(positions)#get the extrems tails of the cand position in the tuple. ex    17           121            187
            i = 0
            twordcount = 0
            while twordcount<2:
                i += 1
                if OCC[cand_posmax+i].cand:
                    key = (self.id, OCC[cand_posmax+i].cand)# tuple(cand_id, nextcand_id)
                    value = tuple(range(cand_posmin,cand_posmax+i+1))
                    found.setdefault(key, set()).add((cand_posmax,cand_posmax+i))
                    break
                elif OCC[cand_posmax+i].tword:
                    twordcount += 1
        return found

    def _unlink(self, occurrences):#to remove the pointed occurrences in the where att of the cand
        self.where.remove(occurrences)

    def recession(self, recession_threshold, OCC):
        if len(self.where) < recession_threshold and not self.name:
            for occurrences in self.where:#to retrieve all the occ
                for position in occurrences:
                    OCC[position].recession()#remove the actual link to a cand in occ instance and replace it by the previous one
            return True#to destry the CAND


class Nucleus(candidat):
    '''
    on cherche des mots rattachés à n'importe quel candidat par un mot de schéma.
    ex: couleurs de FLEUR, couleur de MUR, colleur de CARTON (c'est un exemple problematique)
    -> captera couleur.
    '''
    #TODO
    # inclusion ou non de t_word dans les fenetres de nucleus? then not expa inside nucleus


    def __init__(self, **kwargs):
        super(nucleus, self).__init__(**kwargs)

    def _search_all_twords(self, OCC):
        for occur in OCC:
            #TODO evaluate if this is too slow and not a good benefit for word spoting
            for where in self.where:#try to match any of the shapes that allready matched
                if occur not in self.where and occur.soft_eguality(where):
                    self.where.add((occur,))#add the position (as a tuple of 1 integer) of the occurrence in soft equality
                    break

    def _twords2nuc(self, OCC):
        for new_nuc in self.where:#self.where is a set of tuple of one integer: set((1,), (5,), (18,))
            old_cand = OCC[new_nuc[0]].set_cand(self.id)
            #if old_cand:#not very likely / impossible?

    def build(self, OCC):
        self._search_all_twords(OCC)#search for all the occurrences of this nex nucleus in the whole text
        self._twords2nuc(OCC)#transform the twords in nucleus
