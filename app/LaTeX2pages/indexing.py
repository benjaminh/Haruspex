#!/usr/bin/env python3
# encoding: utf-8

import os
import re
import json


RcaptionPict = re.compile(r'(?<=\\caption{)([^}]*)(?=})', re.UNICODE) #recupère la légende de l'image (contenu de caption)
Rcaption = re.compile(r'(\\caption)([^}]*})', re.UNICODE) #récupère toute la commande caption
Rfootnote = re.compile(r'(\\footnote[^}]*})', re.UNICODE) #récupere l'ensemble (la footnote) pour le supprimer
RcontenuFootnote = re.compile(r'(?<=\\footnote{)([^}]*)(?=})', re.UNICODE) # recupère le contenu de la footnote
RcontenuFootnotetext = re.compile(r'(?<=\\footnotetext{)([^}]*)(?=})', re.UNICODE) # recupère le contenu de la footnotetext

Rtitresection = re.compile(r'(?<=\\section{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitresubsection = re.compile(r'(?<=\\subsection{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitresubsubsection = re.compile(r'(?<=\\subsubsection{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitreparagraph = re.compile(r'(?<=\\paragraph{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)

RibidOpCit = re.compile(r'(ibid|op\.\s?cit\.)', re.IGNORECASE)
RopCitcontenu = re.compile(r'((?:[A-Z]*[^A-Z]*){,2})(?=op\.\s?cit\.|ibid|Ibid|Op. Cit|loc. cit.|Loc. cit.)(?u)') # catch ce qui précède un op. cit. jusqu'à rencontrer deux lettres majuscules -> donne l'élément cité.
# RopCitcontenu = re.compile(r'([A-Z]*[^A-Z]*)(?=op\.\s?cit.)', re.UNICODE) # catch ce qui précède un op. cit. jusqu'à rencontrer une lettre majuscule -> donne l'élément cité.
Rpages = re.compile(r'(\Wpp?\W?\W?[\d\s,-]+)', re.UNICODE) # catch les numéros de page dans une citation

Ranycommand = re.compile(r'\\\w*\[?\{?[^\}|\]]*\}?\]?')
Rall_postbiblio = re.compile(r'(bibliograph.?.?.?{.*}\n|bibliograph.?.?.?\n).*(?siu)')
Rpictname = re.compile(r'(?<=\\includegraphics{)([^}]*)(?=})') # catch the picture name and its folder (the content of the includegraphics command)

refdict = {}
pictdict = {}
pagesdict = {}



class Picture:
    def __init__(self, line):
        self.line = line
        self.id = 0
        self.file = ""
        self.caption = ""
        self.where = ""

    def getdata(self):
        afile = re.findall(Rpictname, self.line)
        self.file = afile[0]
        acaption = re.findall(RcaptionPict, self.line)
        if acaption:
            self.caption = acaption[0]
        else:
            self.caption = None





class Reference:
    def __init__(self, line):
        self.hascontent = False
        self.line = line
        self.id = 0
        self.content = ""
        self.where = ""

    def replaceopcit_incontent(self):
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
            print('NO REFERENCE FOUND FOR THIS ibidem: n°', self.id, '\ncontenant: ', self.content)
            self.content = 'NO REFERENCE FOUND FOR THIS ibidem in ref n°: ' + str(self.id) + ' \tconaining: ' + self.content

    def check(self):
        if self.content:
            self.hascontent = True

    def getdata(self):
        '''  fill the content of the ref instaance from the given textline '''
        acontent = re.findall(RcontenuFootnote, self.line)
        if not acontent:
            acontent = re.findall(RcontenuFootnotetext, self.line)
        if acontent:
            self.content = acontent[0]
        if re.search(RibidOpCit, self.content):
            print('OP CIT FOUND in ref n°' + str(self.id))
            self.replaceopcit_incontent()
        self.check()



class Counter:
    def __init__(self):
        self.paragraphnum = 0
        self.subsubsectionnum = 0
        self.subsectionnum =  0
        self.sectionnum =  0
        self.pictnum = 0
        self.refnum = 0

    def pageincrement_get(self, level):
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
        pagenumber = str(self.sectionnum) + '_' + str(self.subsectionnum) + '_' + str(self.subsubsectionnum) + '_' + str(self.paragraphnum)
        value = (self.paragraphnum, self.subsubsectionnum, self.subsectionnum, self.sectionnum, pagenumber)
        return value

    def increment_get(self, what):
        if what == 'pict':
            self.pictnum += 1
            return self.pictnum
        if what == 'ref':
            self.refnum += 1
            return self.refnum



class Page:
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
        self.word_nb_page = 0
        self.valid = False

    def titling(self):
        if r"paragraph" in self.firstline:
            title = re.findall(Rtitreparagraph, self.firstline)
            self.title = title[0]
            return 4
        if r"subsubsection" in self.firstline:
            title = re.findall(Rtitresubsubsection, self.firstline)
            self.title = title[0]
            return 3
        if r"subsection" in self.firstline:
            title = re.findall(Rtitresubsection, self.firstline)
            self.title = title[0]
            return 2
        if r"section" in self.firstline:
            title = re.findall(Rtitresection, self.firstline)
            self.title = title[0]
            return 1

    def numbering(self, args):
        paragraphnum, subsubsectionnum, subsectionnum, sectionnum, pagenumber = args
        self.sectionnum = sectionnum
        self.subsectionnum = subsubsectionnum
        self.subsubsectionnum = subsubsectionnum
        self.paragraphnum = paragraphnum
        self.number = pagenumber

    def autoclean(self):
        content = re.sub(Rfootnote, '', self.text_rawcontent)
        content = re.sub(Rall_postbiblio, '', content)
        content = re.sub(Rcaption, '', content)
        content = re.sub(Ranycommand, '', content)
        content = re.sub(r'\n\n+', '\n', content)
        content = re.sub(r'\{.*\}', '', content)
        self.text_content = content
        self.word_nb_page = len(re.findall(r'(\w+)(?u)', self.text_content))

    def __repr__(self):
        # return "####\n page number: {}\n word count: {}\n page title: {}\n references : {}\n pictures: {}".format(self.number, self.word_nb_page, self.title, self.refs, self.picts)
        if self.valid:
            return "page # {}, created".format(self.number)
        else:
            return "page # {}, invalid (but created): too few words".format(self.number)

    def json_obj(self):
        data = {
                'paragraphnum': self.paragraphnum,
                'subsubsectionnum': self.subsubsectionnum,
                'subsectionnum': self.subsectionnum,
                'sectionnum': self.sectionnum,
                'pagenumber': self.number,
                'title': self.title,
                'word_nb': self.word_nb_page,
                'content' : self.text_content,
                'references' : self.refs,
                'pictures' : self.picts,
                'author' : self.author,
                'date' : self.date,
                }
        return data











def writePages_and_txt4ana(OrigineFile, write_lastsection, mini_size, step, decoupeParagraphe, author_name, date):
    #getting the last cleaned file
    OrigineFileName = re.findall(r'(?<=/|\\)([^/]+)(?=\.tex)', OrigineFile)
    OrigineFileName	= str(OrigineFileName[0])
    extensionEtapePrec = '.Step' + str(step-1) + '.txt'
    cleanfilename = 'BeingClean/' + OrigineFileName + extensionEtapePrec
    author = author_name
    date_pub = date
    newpage = None
    counter = Counter()
    pagesordered = []
    data = {}

    with open(cleanfilename, 'r', encoding = 'utf8') as text:
        # text = cleanfile.readlines()

        for line in text:
            if re.match(r'(\\.*section)|(\\paragraph)', line):
                if newpage:
                    newpage.autoclean()
                    if newpage.word_nb_page > mini_size:
                        newpage.valid = True
                    pagesordered.append(newpage.number)
                    pagesdict[newpage.number] = newpage
                newpage = Page(line, author, date_pub)
                level = newpage.titling()
                newpage.numbering(counter.pageincrement_get(level))

            if re.match(r'\\includegraphics', line):
                line = line + next(text)
                newpict = Picture(line)
                newpict.id = counter.increment_get('pict')
                newpict.getdata()
                newpict.where = newpage.number
                newpict.id = counter.increment_get('pict')
                pictdict[newpict.id] = newpict
                newpage.picts.append(newpict.id)

            if re.search(Rfootnote, line):
                foottext = re.findall(Rfootnote, line)
                for footnote in foottext:
                    newref = Reference(footnote)
                    newref.id = counter.increment_get('ref')
                    newref.getdata()
                    newref.where = newpage.number
                    refdict[newref.id] = newref
                    newpage.refs.append(newref.id)
                newpage.text_rawcontent += line

            else:
                if newpage:
                    newpage.text_rawcontent += line

        if write_lastsection:
            newpage.autoclean()
            pagesdict[newpage.number] = newpage

    for pageobj in pagesordered:
        print(pagesdict[pageobj])

#writing output files
    with open('text4ana.txt', 'w', encoding = 'utf-8') as txt4ana:
        for pagenum in pagesordered:
            # txt4ana.write(pageobj.title)
            txt4ana.write('\nwxcv' + pagesdict[pagenum].number + 'wxcv\n')
            txt4ana.write(pagesdict[pagenum].title)
            txt4ana.write(pagesdict[pagenum].text_content)

    with open('pages/allpages.json', 'w', encoding = 'utf-8') as jsonpages:
        for pagenum in pagesdict:
            data[pagenum] = pagesdict[pagenum].json_obj()
        json.dump(data, jsonpages, ensure_ascii=False, indent=4)

    imagin = {}
    with open('pages/images.json', 'w', encoding = 'utf-8') as imagesfile:
        for pictid in pictdict:
            imagin.setdefault(pictdict[pictid].where, {}).update({pictdict[pictid].file : pictdict[pictid].caption})
        json.dump(imagin, imagesfile, ensure_ascii=False, indent=4)

    referin = {}
    with open('pages/references.json', 'w', encoding = 'utf-8') as refsfile:
        for refid in refdict:
            referin[refid] = refdict[refid].content
        json.dump(referin, refsfile, ensure_ascii=False, indent=4)
