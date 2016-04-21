#!/usr/bin/env python3
# encoding: utf-8
from py2neo import Graph, Node, Relationship, authenticate
import re


RcaptionPict = re.compile(r'(?<=\\caption{)([^}]*)(?=})', re.UNICODE) #recupère la légende de l'image (contenu de caption)
Rcaption = re.compile(r'(\\caption)([^}]*})', re.UNICODE) #récupère toute la commande caption
Rfootnote = re.compile(r'(\\footnote[^}]*})', re.UNICODE) #récupere l'ensemble (la footnote) pour le supprimer
RcontenuFootnote = re.compile(r'(?<=\\footnote{)([^}]*)(?=})', re.UNICODE) # recupère le contenu de la footnote
RcontenuFootnotetext = re.compile(r'(?<=\\footnotetext{)([^}]*)(?=})', re.UNICODE) # recupère le contenu de la footnotetext

Rtitresection = re.compile(r'(?<=\\section{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitresubsection = re.compile(r'(?<=\\subsection{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitresubsubsection = re.compile(r'(?<=\\subsubsection{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitreparagraph = re.compile(r'(?<=\\paragraph{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rfilename = re.compile(r'(?<=\\filename{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)

RibidOpCit = re.compile(r'(ibid|op\.\s?cit\.)', re.IGNORECASE)
RopCitcontenu = re.compile(r'((?:[A-Z]*[^A-Z]*){,2})(?=op\.\s?cit\.|ibid|Ibid|Op. Cit|loc. cit.|Loc. cit.)(?u)') # catch ce qui précède un op. cit. jusqu'à rencontrer deux lettres majuscules -> donne l'élément cité.
# RopCitcontenu = re.compile(r'([A-Z]*[^A-Z]*)(?=op\.\s?cit.)', re.UNICODE) # catch ce qui précède un op. cit. jusqu'à rencontrer une lettre majuscule -> donne l'élément cité.
Rpages = re.compile(r'(\Wpp?\W?\W?[\d\s,-]+)', re.UNICODE) # catch les numéros de fiche dans une citation

Ranycommand = re.compile(r'\\\w+([\[|\{]?\w*[\]|\}]?){,2}')
Rall_postbiblio = re.compile(r'(bibliograph.?.?.?{.*}\n|bibliograph.?.?.?\n).*(?siu)')
Rpictname = re.compile(r'(?<=\\includegraphics{)([^}]*)(?=})') # catch the picture name and its folder (the content of the includegraphics command)


class Picture:
    def __init__(self, line):
        self.line = line#internal stuff for the method get-data()
        self.id = 0
        self.file = ""#path to the pictfile
        self.caption = ""
        self.where = ""#fiche.number
        self._node = None

    def getdata(self):
        afile = re.findall(Rpictname, self.line)
        self.file = afile[0]
        acaption = re.findall(RcaptionPict, self.line)
        if acaption:
            self.caption = acaption[0]
        else:
            self.caption = None

    def create_node(self,graph_db):
        pict_properties = {'file': self.file, 'caption': self.caption, }
        self._node = Node.cast(pict_properties)
        self._node.labels.add('picture')
        graph_db.create(self._node)

    def write_row(self, output):
        pict_properties = ['pict', self.where, self.file, self.caption]
        output.writerow(pict_properties)




class Reference:
    def __init__(self, line):
        self.hascontent = False
        self.line = line#internal stuff for the method get-data()
        self.id = 0
        self.content = ""#the reference as written in the text (managing op.cit. and other latin stuffs)
        self.where = ""#fiche.number
        self._node = None

    def replaceopcit_incontent(self, refdict):
        ''' automically porcessed.
        modifies the content in the ref if this ref contains anything (op.cit. ibid. ...) pointing to a previous reference'''
        target = re.findall(RopCitcontenu, self.content)
        target = target[0]
        elements = re.findall(r'([A-Z][\w]*)(?u)', target)
        Relements = r'\b' + '.{,4}'.join(elements) + r'\b(?iu)'
        prev_ref = ''
        for ref in refdict:
            if re.search(Relements, refdict[ref].content):
                prev_ref = refdict[ref].content
                break
        if prev_ref:
            now_pagenum = re.findall(Rpages, self.content) # catch les nombres ou espaces ou virgule ou tirets après p ou pp ou p. ou pp.
            prev_pagenum = re.findall(Rpages, prev_ref)
            if now_pagenum and prev_pagenum:
                self.content = re.sub(Rpages, now_pagenum[0], prev_ref)
            elif now_pagenum and not prev_pagenum:
                self.content = prev_ref + now_pagenum[0]
            else:
                self.content = prev_ref
        else:
            #print('NO REFERENCE FOUND FOR THIS ibidem: n°', self.id, '\ncontenant: ', self.content)
            self.content = 'NO REFERENCE FOUND FOR THIS ibidem in ref n°: ' + str(self.id) + ' \tconaining: ' + self.content

    def check(self):
        if self.content:
            self.hascontent = True

    def getdata(self, refdict):
        '''  fill the content of the ref instance from the given textline '''
        acontent = re.findall(RcontenuFootnote, self.line)
        if not acontent:
            acontent = re.findall(RcontenuFootnotetext, self.line)
        if acontent:
            self.content = acontent[0]
        if re.search(RibidOpCit, self.content):
            #print('OP CIT FOUND in ref n°' + str(self.id))
            self.replaceopcit_incontent(refdict)
        self.check()

    def create_node(self,graph_db):
        # Ajouter propriétés du type "modified" ?
        ref_properties = {'content': self.content, }
        self._node = Node.cast(ref_properties)
        self._node.labels.add('ref')
        graph_db.create(self._node)

    def write_row(self, output):
        ref_properties = ['ref', self.where, self.content]
        output.writerow(ref_properties)


class Counter:
    '''
    just a counter for the section, subsection, and other stuff
    '''
    def __init__(self):
        self.file_num = 0
        self.paragraphnum = 0
        self.subsubsectionnum = 0
        self.subsectionnum =  0
        self.sectionnum =  0
        self.pictnum = 0
        self.refnum = 0

    def ficheincrement_get(self, level):
        if level ==0:
            self.file_num += 1
            self.sectionnum = 0
            self.subsectionnum = 0
            self.subsubsectionnum = 0
            self.paragraphnum = 0
        if level == 1:
            self.sectionnum += 1
            self.subsectionnum = 0
            self.subsubsectionnum = 0
            self.paragraphnum = 0
        if level == 2:
            self.subsectionnum += 1
            self.subsubsectionnum = 0
            self.paragraphnum = 0
        if level == 3:
            self.subsubsectionnum += 1
            self.paragraphnum = 0
        if level == 4:
            self.paragraphnum += 1
        fichenumber = str(self.file_num) + '_' + str(self.sectionnum) + '_' + str(self.subsectionnum) + '_' + str(self.subsubsectionnum) + '_' + str(self.paragraphnum)
        value = (self.paragraphnum, self.subsubsectionnum, self.subsectionnum, self.sectionnum, self.file_num, fichenumber)
        return value

    def increment_get(self, what):
        if what == 'pict':
            self.pictnum += 1
            return self.pictnum
        if what == 'ref':
            self.refnum += 1
            return self.refnum



class Fiche:
    def __init__(self, line, author, date_pub):
        self.firstline = line
        self.paragraphnum = 0
        self.subsubsectionnum = 0
        self.subsectionnum =  0
        self.sectionnum =  0
        self.number = ""
        self.title = ""
        self.text_rawcontent = ""
        self.text_content = ""
        self.refs = []
        self.picts = []
        self.author = author
        self.date = date_pub
        self.word_nb_fiche = 0
        self.valid = False
        self.file_num = 0
        self._node = None

    def titling(self):
        if re.match(r'\\filename', self.firstline):
            title = re.findall(Rfilename, self.firstline)
            self.title = title[0]
            return 0
        elif re.match(r'\\paragraph', self.firstline):
            title = re.findall(Rtitreparagraph, self.firstline)
            self.title = title[0]
            return 4
        elif re.match(r'\\subsubsection', self.firstline):
            title = re.findall(Rtitresubsubsection, self.firstline)
            self.title = title[0]
            return 3
        elif re.match(r'\\subsection', self.firstline):
            title = re.findall(Rtitresubsection, self.firstline)
            self.title = title[0]
            return 2
        elif re.match(r'\\section', self.firstline):
            title = re.findall(Rtitresection, self.firstline)
            self.title = title[0]
            return 1


    def numbering(self, args):
        paragraphnum, subsubsectionnum, subsectionnum, sectionnum, filenumber, fichenumber = args
        self.file_num = filenumber
        self.sectionnum = sectionnum
        self.subsectionnum = subsubsectionnum
        self.subsubsectionnum = subsubsectionnum
        self.paragraphnum = paragraphnum
        self.number = fichenumber

    def autoclean(self):
        content = re.sub(Rfootnote, '', self.text_rawcontent)
        content = re.sub(Rall_postbiblio, '', content)
        content = re.sub(Rcaption, '', content)
        content = re.sub(Ranycommand, '', content)
        content = re.sub(r'\n\n+', '\n', content)
        content = re.sub(r'\{.*\}', '', content)
        self.text_content = content
        self.word_nb_fiche = len(re.findall(r'(\w+)(?u)', self.text_content))

    def __repr__(self):
        # return "####\n fiche number: {}\n word count: {}\n fiche title: {}\n references : {}\n pictures: {}".format(self.number, self.word_nb_fiche, self.title, self.refs, self.picts)
        if self.valid:
            return "fiche # {}, created".format(self.number)
        else:
            return "fiche # {}, invalid (but created): too few words".format(self.number)

    def json_obj(self):
        data = {
                'file_num': self.file_num,
                'paragraphnum': self.paragraphnum,
                'subsubsectionnum': self.subsubsectionnum,
                'subsectionnum': self.subsectionnum,
                'sectionnum': self.sectionnum,
                'fichenumber': self.number,
                'title': self.title,
                'word_nb': self.word_nb_fiche,
                'references' : self.refs,
                'pictures' : self.picts,
                'author' : self.author,
                'date' : self.date,
                }
        return data

    def create_node(self,graph_db):
        # Ajouter propriétés du type "modified" ?
        fiche_properties = {'doc_position': self.number, 'titre': self.title,
                            'auteur': self.author, 'date_creation': self.date,}
        self._node = Node.cast(fiche_properties)
        self._node.labels.add('fiche')
        graph_db.create(self._node)

    def create_relations(self, graph_db, pictdict, refdict):
        for ref in self.refs:
            #Build a relation between the nodes of each the fiche and each fiche's references
            ref_node = refdict[ref]._node
            relatio = Relationship.cast(ref_node, ("ref"), self._node)
            graph_db.create(relatio)
        #Build a relation between the nodes of each the fiche and each fiche's pictures
        for pict in self.picts:
            pict_node = pictdict[pict]._node
            relatio = Relationship.cast(pict_node, ("pict"), self._node)
            graph_db.create(relatio)

    def write_row(self, output):
        dates = re.findall(r'[1|2]\d\d\d', self.title)
        if dates:
            date = dates[0]
        else:
            date = ''
        fiche_properties = [self.file_num, self.number, self.title, date]
        output.writerow(fiche_properties)
