#!/usr/bin/env python3
# encoding: utf-8

import os
import re
import json

# Picts = open('HallesA/pages/images', 'w', encoding = 'utf8')
# Refs = open('HallesApages/references', 'w', encoding = 'utf8')

#RnamePict = re.compile(r"(?<=\\includegraphics{" + re.escape(DossierImage) + r')(.*)(?=}), re.UNICODE) #regex déplacée dans la fonction "découpe" pour récupérer le dossier où sont placées les images #recupère le nom de l'image (chemin dans son dossier) après suppression des para d'affichage (cf ci-dessus)
RcaptionPict = re.compile(r'(?<=\\caption{)([^}]*)(?=})', re.UNICODE) #recupère la légende de l'image
Rfootnote = re.compile(r'(\\footnote)([^}]*})', re.UNICODE) #récupere l'ensemble (la footnote) pour le supprimer
RcontenuFootnote = re.compile(r'(?<=\\footnote{)([^}]*)(?=})', re.UNICODE) # recupère le contenu de la footnote
RcontenuFootnotetext = re.compile(r'(?<=\\footnotetext{)([^}]*)(?=})', re.UNICODE) # recupère le contenu de la footnotetext
RnombreuxSauts = re.compile(r'((?<=\n)(\s+)(?=\S))', re.UNICODE)

Rtitresection = re.compile(r'(?<=\\section{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitresubsection = re.compile(r'(?<=\\subsection{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitresubsubsection = re.compile(r'(?<=\\subsubsection{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)
Rtitreparagraph = re.compile(r'(?<=\\paragraph{)(.*)(?=})', re.UNICODE) #récupere le contenu (le titre)

RibidOpCit = re.compile(r'(ibid|op\.\s?cit\.)', re.IGNORECASE)
# Ribid = re.compile(r'(ibid)', re.IGNORECASE)
# RopCit = re.compile(r'(op\.\s?cit\.)', re.IGNORECASE) # catch les op.cit.
RopCitcontenu = re.compile(r'((?:[A-Z]*[^A-Z]*){,2})(?=op\.\s?cit\.|ibid|Ibid|Op. Cit|loc. cit.|Loc. cit.)(?u)') # catch ce qui précède un op. cit. jusqu'à rencontrer deux lettres majuscules -> donne l'élément cité.
# RopCitcontenu = re.compile(r'([A-Z]*[^A-Z]*)(?=op\.\s?cit.)', re.UNICODE) # catch ce qui précède un op. cit. jusqu'à rencontrer une lettre majuscule -> donne l'élément cité.
Rpages = re.compile(r'(\Wpp?\W?\W?[\d\s,-]+)', re.UNICODE) # catch les numéros de page dans une citation


# créer la fiche qui contient tout les éléments amassés jusqu'à cette rupture (c'est à dire: créer la fiche correspondant à la section précédente)
def EcrireSectionPrecedente(identifiant, taille, tailleMinimum, titreSection, ContenuTxtSection, ref_insection, nomAuteur, datecreation):
    # print (identifiant + '\t' + str(taille))
    if taille > tailleMinimum:
        nomfichierFiche = 'pages/fiche' + identifiant + '.txt'
        with open(nomfichierFiche, 'w', encoding = 'utf8') as fiche:
            fiche.write('fiche n° '+ identifiant + '\n')
            fiche.write('titre: ' + titreSection + '\n')
            fiche.write('auteur: ' + nomAuteur + '\n')
            fiche.write('date: ' + datecreation+ '\n\n\n')
            contenujoin = '\n'.join(ContenuTxtSection)
            contenujoin = re.sub(RnombreuxSauts, "\n", contenujoin)
            contenujoin = re.sub(Rfootnote, "", contenujoin)
            fiche.write(contenujoin)
            fiche.write('\n\n\nRéférences associées: ' )
            for identifiantRef in ref_insection.keys():
                fiche.write(str(identifiantRef) + ' ')
            fiche.close()

def write_txt4ana(identifiant, titreSection, ContenuTxtSection):
    with open("text4ana.txt", 'a', encoding = 'utf8') as text4ana:
        text4ana.write('\n\nwxcv'+ identifiant + 'wxcv\n')
        text4ana.write(titreSection+ '\n')
        contenujoin = '\n'.join(ContenuTxtSection)
        contenujoin = re.sub(RnombreuxSauts, "\n", contenujoin)
        contenujoin = re.sub(Rfootnote, "", contenujoin)
        text4ana.write(contenujoin)



def Image(thisline, nextline, RnamePict):
    PictName = re.findall(RnamePict, thisline)
    PictLegende = re.findall(RcaptionPict, nextline)
    if not PictLegende:
        PictLegende = ['Pas_de_legende']
    return PictName[0], PictLegende[0]

# Fonction pour enregistrer les footnotes en tant que références, placées de manière linéaires au fil du texte. Une même référence citée plusieurs fois, donnera lieu à plusieurs RefID (sale pratique d'écriture oblige)
def References(thisline, ref_insection, dicorefs):
    linereferences = re.findall(RcontenuFootnote, thisline) # attention il peut y avoir plusieurs footnote par ligne
    linereferences += re.findall(RcontenuFootnotetext, thisline)
    RefID = len(dicorefs.keys())
    # en cas de ibid, ou op. cit. la tache devient compiquée...
    #il y a ici une approximation qui consiste à reprendre la référence précédente. Mais impossible de savoir si l'utilisation de ladite reference et argumentée différement...
    for refere in linereferences:
        RefID += 1
        if not re.search(RibidOpCit, refere):
            dicorefs[RefID] = refere
            ref_insection[RefID] = refere

        elif re.search(RibidOpCit, refere):
            # print('\nop.cit. ou ibid. found in footnote n°' + str(RefID) + ': check the result manualy please!')
            versQuoi = re.findall(RopCitcontenu, refere)
            versQuoi = versQuoi[0]
            elements = re.findall(r'([A-Z][\w]*)(?u)', versQuoi)
            Relements = r'\b' + '.{,4}'.join(elements) + r'\b(?iu)'
            ref_prec = []
            for value in dicorefs.values():
                if re.search(Relements, value):
                    ref_prec = value
                    # print('####\nreferenceprecedente', ref_prec)
                    break
            # ref_prec = [value for key, value in dicorefs.items() if re.search(Relements, value)] # cherche dans le dico une valeur qui correpsond à ce qu'on à catché comme étant op. cité.
            if ref_prec:
                pages_now = re.findall(Rpages, refere) # catch les nombres ou espaces ou virgule ou tirets après p ou pp ou p. ou pp.
                pages_prec = re.findall(Rpages, ref_prec)
                if pages_now and pages_prec:
                    ref_prec_mod = re.sub(Rpages, pages_now[0], ref_prec)
                    dicorefs[RefID] = ref_prec_mod
                    ref_insection[RefID] = ref_prec_mod
                elif pages_now and not pages_prec:
                    ref_prec_mod = ref_prec + pages_now[0]
                    dicorefs[RefID] = ref_prec_mod
                    ref_insection[RefID] = ref_prec_mod
                elif not pages_now:
                    dicorefs[RefID] = ref_prec
                    ref_insection[RefID] = ref_prec

            else:
                print('NO REFERENCE FOUND FOR THIS ibidem: n°', RefID, '\ncontenant: ', refere)
                ref = 'NO REFERENCE FOUND FOR THIS ibidem n°: ' + str(RefID) + '  contenant: ' + refere
                dicorefs[RefID] = ref
                ref_insection[RefID] = ref
            # except:
            #     print('op.cit ou ibid in footnote n°', str(RefID), 'cause problème, impossible de détécter ce à queoi cela se refere.')
    return dicorefs, ref_insection



#########################################################
##########################################################
####fonction principale qui est appelée par LaTeX2Fiche
def writePages_and_txt4ana(OrigineFile, conclusion, tailleMini, step, decoupeParagraphe, nom_auteur, date, DossierImage):
    if os.path.isfile('text4ana.txt'):
        os.remove('text4ana.txt') # remove the text written for ana in last session (otherwise it is being duplicated)
    #getting the last cleaned file
    OrigineFileName = re.findall(r'(?<=/|\\)([^/]+)(?=\.tex)', OrigineFile)
    OrigineFileName	= str(OrigineFileName[0])
    extensionEtapePrec = '.Step' + str(step-1) + '.txt'
    FichierPropre = 'BeingClean/' + OrigineFileName + extensionEtapePrec
    dicorefs = {}
    dicopict = {}
    Pict = {}
    RefID = 0
    if DossierImage == 'automatic': #pour retrouver le dossier Image tel que Writer2Latex le crée
        DossierImage = re.sub('_', '', OrigineFileName)
        DossierImage = DossierImage + '-img/'
    RpictName = re.compile(r"(?<=\\includegraphics{" + re.escape(DossierImage) + r')(.*)(?=})', re.UNICODE) #recupère le nom de l'image (dans son dossier)

    with open(FichierPropre, 'r', encoding = 'utf8') as fichierpropre:
        text = fichierpropre.readlines()

        titre = " " #pour amorcer
        ref_insection = {}
        contenutxt = []
        i = 0
        sec = 0
        subsec = 0
        subsubsec = 0
        parag = 0
        NbMotsSect = 0

        for line in text:
            i += 1
            NbMotsSect +=  len(re.findall(r'(\w+)(?u)', line))
            # NbMotsSect += CompteurMots(line)
            if not decoupeParagraphe:
                IDf = str(sec) + "_" + str(subsec) + "_" + str(subsubsec)
            else:
                IDf = str(sec) + "_" + str(subsec) + "_" + str(subsubsec) + "_" + str(parag)

            if "\includeg" in line:
                PictName, PictLegende = Image(line, text[i], RpictName)
                Pict[PictName] = PictLegende
                dicopict.setdefault(IDf, {}).update(Pict)
                del(Pict[PictName])
                # dicopict[IDf][PictName] = PictLegende

            if "\\footnote" in line:
                dicorefs, ref_insection = References(line, ref_insection, dicorefs)

            #il y a une option pour découper les \paragraph en tant que sousoussoussection en cas de manuscrit mal structuré...
            #sinon les \paragraph deviennent des paragraphes (avec saut de ligne tout simplement)
            if not decoupeParagraphe:
                if "\\paragraph" in line:
                    titreparagraphe = re.findall(Rtitreparagraph, line)
                    titreparagraphe = "\n" + titreparagraphe[0]
                    contenutxt.append(titreparagraphe)
            else:
                if "\\paragraph" in line:
                    write_txt4ana(IDf, titre, contenutxt)
                    EcrireSectionPrecedente(IDf, NbMotsSect, tailleMini, titre, contenutxt, ref_insection, nom_auteur, date)
                    contenutxt = []
                    ref_insection = {}
                    NbMotsSect = 0
                    ti = re.findall(Rtitreparagraph, line)
                    titre = ti[0]
                    parag += 1


            if line[0] != ("\\" or "%"): #capte les lignes de texte type 'contenu' mais pa les lignes commençant par \ (problème) ou par une ligne commentée %
                contenutxt.append(line)

            if re.match(r'\\footnote', line): #capte les lignes qui commencent par une footnote (donc qui commencent par un \). C'est bizare mais ça existe
                contenutxt.append(line)

            if "\\section" in line:
                write_txt4ana(IDf, titre, contenutxt)
                EcrireSectionPrecedente(IDf, NbMotsSect, tailleMini, titre, contenutxt, ref_insection, nom_auteur, date)
                contenutxt = []
                ref_insection = {}
                NbMotsSect = 0
                ti = re.findall(Rtitresection, line)
                titre = ti[0]
                sec += 1
                subsec = 0
                subsubsec = 0
                parag = 0

            if "\\subsection" in line:
                write_txt4ana(IDf, titre, contenutxt)
                EcrireSectionPrecedente(IDf, NbMotsSect, tailleMini, titre, contenutxt, ref_insection, nom_auteur, date)
                contenutxt = []
                ref_insection = {}
                NbMotsSect = 0
                ti = re.findall(Rtitresubsection, line)
                titre = ti[0]
                subsec += 1
                subsubsec = 0
                parag = 0

            if "\\subsubsection" in line:
                write_txt4ana(IDf, titre, contenutxt)
                EcrireSectionPrecedente(IDf, NbMotsSect, tailleMini, titre, contenutxt, ref_insection, nom_auteur, date)
                contenutxt = []
                ref_insection = {}
                NbMotsSect = 0
                ti = re.findall(Rtitresubsubsection, line)
                titre = ti[0]
                subsubsec += 1
                parag = 0

            if conclusion in line:
                write_txt4ana(IDf, titre, contenutxt)
                EcrireSectionPrecedente(IDf, NbMotsSect, tailleMini, titre, contenutxt, ref_insection, nom_auteur, date)

        with open('pages/references.json', 'w', encoding = 'utf8') as reffile:
            json.dump(dicorefs, reffile, ensure_ascii=False, indent=4)
        with open('pages/images.json', 'w', encoding = 'utf8') as pictfile:
            json.dump(dicopict, pictfile, ensure_ascii=False, indent=4)
