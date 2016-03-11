#!/usr/bin/env python3
# encoding: utf-8

from os.path import join
import re
import json
from L2P_Objects import Fiche, Reference, Picture, Counter
from py2neo import neo4j, Node, Relationship

Rfootnote = re.compile(r'(\\footnote[^}]*})', re.UNICODE) #récupere l'ensemble (la footnote) pour le supprimer

refdict = {}
pictdict = {}
fichesdict = {}


def write_jsons(working_directory, fichesdict, fichesordered):
    '''
    write 2 json files, output of the processand input for ana
    '''
    data = {}
    with open(join(working_directory, 'pages', 'output', 'content.json'), 'w', encoding = 'utf-8') as jsonfiches:
        for fichenum in fichesdict:
            data[fichenum] = fichesdict[fichenum].text_content
        json.dump(data, jsonfiches, ensure_ascii=False, indent=4)

    with open(join(working_directory, 'ANA', 'txt4ana'), 'w', encoding = 'utf-8') as txt4ana:
        for fichenum in fichesordered:
            # txt4ana.write(ficheobj.title)
            txt4ana.write('\nwxcv' + str(fichesdict[fichenum].number) + 'wxcv\n')
            txt4ana.write(fichesdict[fichenum].title)
            txt4ana.write(fichesdict[fichenum].text_content)

def create_nodes_and_rels(fichesdict, pictdict, refdict, graph_db):
    '''
    this function creates nodes
    when creating a node,
    the Object (Picture, Reference, Fiche) get an node_id attribute
    '''

    for pictnum in pictdict:#Build the node for each pictures
        pictdict[pictnum].create_node(graph_db)
    for refnum in refdict:#Build the node for each reference
        refdict[refnum].create_node(graph_db)
    for fichenum in fichesdict:#Build the node for each page
        #print('CREATING NODE', fichenum)
        fichesdict[fichenum].create_node(graph_db)
        #print('CREATING RELATIONS', fichenum)
        fichesdict[fichenum].create_relations(graph_db, pictdict, refdict)



def writePages_and_txt4ana(working_directory, write_lastsection, mini_size, parag_cut ,auteur, date):
    #getting the last cleaned file
    cleanfilename = join(working_directory, 'pages', 'convertconcat', 'concat.tex')
    author = auteur
    date_pub = date
    newfiche = None
    counter = Counter()
    fichesordered = []
    data = {}
    if parag_cut:
        fiche_delimiter = r'(\\.*section)|(\\paragraph)|(\\filename)'
    else:
        fiche_delimiter = r'(\\.*section)|(\\filename)'

    with open(cleanfilename, 'r', encoding = 'utf8') as text:
        for line in text:
            if re.match(fiche_delimiter, line):
                if newfiche:
                    newfiche.autoclean()
                    if newfiche.word_nb_fiche > mini_size:
                        newfiche.valid = True
                    fichesordered.append(newfiche.number)
                    fichesdict[newfiche.number] = newfiche
                newfiche = Fiche(line, author, date_pub)
                level = newfiche.titling()
                newfiche.numbering(counter.ficheincrement_get(level))

            if re.search(r'\\includegraphics', line) and newfiche:
                line = line + next(text)
                newpict = Picture(line)
                newpict.id = counter.increment_get('pict')
                newpict.getdata()
                newpict.where = newfiche.number
                pictdict[newpict.id] = newpict
                newfiche.picts.append(newpict.id)

            if re.search(Rfootnote, line) and newfiche:
                foottext = re.findall(Rfootnote, line)
                for footnote in foottext:
                    newref = Reference(footnote)
                    newref.id = counter.increment_get('ref')
                    newref.getdata(refdict)
                    newref.where = newfiche.number
                    refdict[newref.id] = newref
                    newfiche.refs.append(newref.id)
                newfiche.text_rawcontent += line

            elif newfiche:
                if newfiche:
                    newfiche.text_rawcontent += line

        if write_lastsection:
            newfiche.autoclean()
            fichesdict[newfiche.number] = newfiche


    print('\n\n###\nnow uploading to neo4j database, this lasts around 15 secondes\n###')
    #writing outputs
    try:
        graph_db = neo4j.GraphDatabaseService()
        # authenticate("localhost:7474", "neo4j", "haruspex")
        # graph_db = Graph()
        graph_db.cypher.execute("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE r,n")
        create_nodes_and_rels(fichesdict, pictdict, refdict, graph_db)
    except:
        print('No neo4j database found on localhost:7474, try to (re)start it')
    print('\n\n###\nnow writting output files\n###')
    write_jsons(working_directory, fichesdict, fichesordered)
    print('NOMBRE DE FICHES', len(fichesdict))
