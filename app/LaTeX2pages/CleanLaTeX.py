#!/usr/bin/env python3
# encoding: utf-8
import os
import re

#  begin regex  ###########################################################
Rtextbf = re.compile(r'(\\textbf{[^\}]*\})', re.UNICODE) #recupère le marqueur textbf et son contenu
Rcontenubf = re.compile(r'(?<=\\textbf{)([^\}]*)(?=})', re.UNICODE) #recupère le contenu de la balise textbf
Rtextit = re.compile(r'(\\textit{[^\}]*\})', re.UNICODE) #recupère le marqueur textit et son contenu
Rcontenuit = re.compile(r'(?<=\\textit{)([^\}]*)(?=})', re.UNICODE) #recupère le contenu de la balise textit
#RcommandeVideOld = re.compile('(^\\\w*(\{\}|[\s\n]|\{[^\w\n]+\}))', re.UNICODE) # récupère les lignes commençant par \ suivies de lettres (commande) puis "blanc" ou acolade contenant "non-lettre" uniquement.
RcommandeVide = re.compile(r'(\\\w*(\{\}|[\s\n]|\{[^\w\n]+\}))', re.UNICODE) # récupère les "mots" commençant par \ suivis de lettres (commande) puis "blanc" ou acolade contenant "non-lettre"
Racolades = re.compile(r"{[^\w\n]*}", re.UNICODE) #recupère les acolades ne contenant que des symboles non mot (à remplacer par le contenu)
RcontenuAcolades = re.compile(r'(?<={)([^\w\n]*)(?=})', re.UNICODE) # récupère le contenu des symboles non mot entre acolades
#Ritem = re.compile(r'(?<=\\item)([^\\]*)(?=\\)(?s)', re.UNICODE) # OBSOLETE recupère le contenu de l'item
Rechapdecaractere = re.compile(r'(\\)(?=[\W_])', re.UNICODE) # recupère le \ avant les caractères échappés et les espaces
RwithPict = re.compile(r'(?<=\\includegraphics)(.*)(?={)', re.UNICODE) #recupère les paramètre d'affichage de la taille de l'image (pour les supp)
RcrochetPict = re.compile(r'(?<=\\caption)([^{]*)(?={)(?s)', re.UNICODE) #recupère les paramètre de la légende (pour les supp)
Rcrochetsection = re.compile(r'(?<=\\section)(.*)(?={)', re.UNICODE) #recupère les paramètre du titre (pour les supp)
Rcrochetsubsection = re.compile(r'(?<=\\subsection)(.*)(?={)', re.UNICODE) #recupère les paramètre du titre (pour les supp)
Rcrochetsubsubsection = re.compile(r'(?<=\\subsubsection)(.*)(?={)', re.UNICODE) #recupère les paramètre du titre (pour les supp)
Rcrochetparagraph = re.compile(r'(?<=\\paragraph)(.*)(?={)', re.UNICODE) #recupère les paramètre du titre (pour les supp)
RdebutLigne = re.compile(r'(\w|\\footnote|«|\(|~|\:| |\t)', re.UNICODE)
RFauxSaut = re.compile(r'([ \t][ \t]*\n)', re.UNICODE)
Rcontenuindex = re.compile(r'(?<=\\index{)([^}]*)(?=})') #OBSOLÈTE (car le contenu est souvent inutile) récupère le contenu d'une commande index
Rindex = re.compile(r'(\\index{[^}]*})') # recupère l'ensemble de la commande index pour la supprimer

#  end regex  ###########################################################


def AcoladeClose(OrigineFile, step):
	with open(OrigineFile, 'r', encoding = 'utf8') as fichierOrigine:
		texteO = fichierOrigine.readlines()
		OrigineFileName = re.findall(r'(?<=/|\\)([^/]+)(?=\.tex)', OrigineFile)
		OrigineFileName	= str(OrigineFileName[0])
		extensionEtape = '.Step' + str(step) + '.txt'
		FileStep1 = 'BeingClean/' + OrigineFileName + extensionEtape
		with open(FileStep1, "w", encoding = 'utf8') as filestep1:
			i = 0
			for ligneO in texteO:
				if "\end{document}" not in texteO[i]:
					i += 1
					ligneO = texteO[i]

					if "{" in ligneO:
						compteur = len(re.findall("{", ligneO))
						compteurF = len(re.findall("}", ligneO))
						while compteur > compteurF:
							texteO[i] = re.sub("\n", " ", texteO[i]) #texte[i] = ligne (la première fois)
							#print (texte[i])
							filestep1.write(texteO[i]) # écrit cette ligne sans le \n
							compteur += len(re.findall("{", texteO[i+1])) #incrémente le compteur avec ce qu'il trouve dans la ligne suivante
							compteurF += len(re.findall("}", texteO[i+1]))
							i += 1 # passe à la ligne suivante
					filestep1.write(texteO[i])
			filestep1.close()
			fichierOrigine.close()
	return 1

#warning: in case of use of mathematics formula with non closed square bracket (eg: an range of values like [1976, 1986[)
def CrochetClose(OrigineFile, step):
	OrigineFileName = re.findall(r'(?<=/|\\)([^/]+)(?=\.tex)', OrigineFile)
	OrigineFileName	= str(OrigineFileName[0])
	extensionEtape = '.Step' + str(step) + '.txt'
	extensionEtapePrec = '.Step' + str(step-1) + '.txt'
	FileStep1 = 'BeingClean/' + OrigineFileName + extensionEtapePrec
	FileStep2 = 'BeingClean/' + OrigineFileName + extensionEtape
	with open(FileStep1, 'r', encoding = 'utf8') as filestep1:
		texteS1 = filestep1.readlines()
		with open(FileStep2, "w", encoding = 'utf8') as filestep2:
			i = 0
			for ligneS1 in texteS1:
				if "\end{document}" not in texteS1[i]:
					i += 1
					ligneS1 = texteS1[i]

					if "[" in ligneS1:
						compteur = len(re.findall("\[", ligneS1))
						compteurF = len(re.findall("\]", ligneS1))
						while compteur > compteurF:
							texteS1[i] = re.sub("\n", " ", texteS1[i]) #texteS1[i] = ligneS1 (la première fois)
							filestep2.write(texteS1[i]) # écrit cette ligne sans le \n
							compteur += len(re.findall("\[", texteS1[i+1])) #incrémente le compteur avec ce qu'il trouve dans la ligne suivante
							compteurF += len(re.findall("\]", texteS1[i+1]))
							i += 1 # passe à la ligne suivante
					filestep2.write(texteS1[i])
			filestep2.close()
			filestep1.close()
	return 1


def Clean(OrigineFile, step):
	OrigineFileName = re.findall(r'(?<=/|\\)([^/]+)(?=\.tex)', OrigineFile)
	OrigineFileName	= str(OrigineFileName[0])
	extensionEtape = '.Step' + str(step) + '.txt'
	extensionEtapePrec = '.Step' + str(step-1) + '.txt'
	FileStep2 = 'BeingClean/' + OrigineFileName + extensionEtapePrec
	FileStep3 = 'BeingClean/' + OrigineFileName + extensionEtape
	with open(FileStep2, 'r', encoding = 'utf8') as filestep2:
		texteS2 = filestep2.readlines()
		with open(FileStep3, "w", encoding = 'utf8') as filestep3:

			for ligne in texteS2:

				#remplace les textbf par du texte simple
				c = re.findall(Rtextbf, ligne)
				d = re.findall(Rcontenubf, ligne)
				i = 0
				while i<len(c):
					ligne = ligne.replace(c[i],d[i])
					i += 1

				#remplace les textit par du texte simple
				e = re.findall(Rtextit, ligne)
				f = re.findall(Rcontenuit, ligne)
				j = 0
				while i<len(c):
					ligne = ligne.replace(e[j],f[j])
					j += 1

				#remplace les caractères spéciaux perdus entre acolade (au sein d'un zone entre acolade souvent, ex: "\footnote{hello world [2015{]}}") par le même caractère sans les sans les acolades
				#au lieux de les virer: ligne = re.sub(r"{[^\w\n]*}", "", ligne) et de perdre des crochets perdus entre acolade par exemple...
				g = re.findall(Racolades, ligne)
				h = re.findall(RcontenuAcolades, ligne)
				k = 0
				while k<len(g):
					ligne = ligne.replace(g[k],h[k])
					k += 1

				if re.match(r'(\[Warning:[^\]]*\])', ligne):
					ligne = re.sub(r'(\[Warning:[^\]]*\])', '', ligne) # supprime les warning image ignored... tant pis pour elles!
					print('Problème avec une image')
				ligne = re.sub(r'\\item', '\n - ', ligne) #remplace les \item par des tiret en sautant une ligne auparavant.
				ligne = re.sub(Rechapdecaractere, "", ligne)
				ligne = re.sub(RcommandeVide, "", ligne) #je ne sais pas pourquoi ça ne marche pas sur footnotemark en pratique
				ligne = re.sub(Rechapdecaractere, "", ligne)
				ligne = re.sub(r"{\\textgreater}", "", ligne)
				ligne = re.sub(r"{\\textquotedbl}", "", ligne)
				ligne = re.sub(r'{\\dots}', '...', ligne)
				ligne = re.sub(r'{\oe}', 'œ', ligne)
				ligne = re.sub(r"{\\textless}", "", ligne)
				ligne = re.sub(r"^\\\w*(\{\}|[\s\n]|\{[^\w\n]+\})", "", ligne)
				ligne = re.sub(r"{[^\w\n]*}", "", ligne)
				ligne = re.sub(RwithPict, "", ligne)
				ligne = re.sub(RcrochetPict, "", ligne)
				ligne = re.sub(Rcrochetsection, "", ligne)
				ligne = re.sub(Rcrochetsubsection, "", ligne)
				ligne = re.sub(Rcrochetsubsubsection, "", ligne)
				ligne = re.sub(Rcrochetparagraph, "", ligne)
				ligne = re.sub(r'\\clearpage', "", ligne)
				ligne = re.sub(r'\\footnotemark', "", ligne)
				ligne = re.sub(Rindex, '', ligne)

			#enlève les passages à la ligne intempestifs dans un même paragraphe
				if re.match(RdebutLigne, ligne) and not re.match(RFauxSaut, ligne):
					ligne = re.sub(r'\n', " ", ligne)
				filestep3.write(ligne)
		filestep3.close()
		filestep2.close()
	return 1
