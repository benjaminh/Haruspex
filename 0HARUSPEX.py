#!/usr/bin/env python3
# encoding: utf-8
from shutil import copyfile
from os.path import join, isfile, exists, dirname, realpath
from os import makedirs, remove, chdir
import re

def setup_dir():
    harupexdir = dirname(realpath(__file__))
    chdir(wd)
    if not exists(join('pages', 'convertconcat', 'convert')):
    	makedirs(join('pages', 'convertconcat', 'convert'))
    if not exists(join('pages','BeingClean')):
    	makedirs(join('pages','BeingClean'))
    if not exists(join('pages','output')):
    	makedirs(join('pages','output'))
    if not isfile(join('pages','L2P_config.json')):
        copyfile(join(harupexdir, 'L2P_configtemplate.json'), join('pages','L2P_config.json'))
    if not exists('ANA/output/'):
        makedirs('ANA/output/')#keywords, what_in_page, where_keyword...
    if not exists('ANA/log/'):
        makedirs('ANA/log/')#log, stuff
    elif isfile('ANA/log/ana.log'):
        remove('ANA/log/ana.log')
    if not isfile('ANA/bootstrap'):
        open('ANA/bootstrap', 'a').close()
    if not isfile('ANA/non_solo.txt'):
        open('ANA/non_solo.txt', 'a').close()#like "touch" in unix
    if not isfile('ANA/extra_emptywords.txt'):
        with open('ANA/extra_emptywords.txt', 'a') as emptyregex:
            emptyregex.write('^\w.?$')
    if not isfile('ANA/extra_stopwords.txt'):
        open('ANA/extra_stopwords.txt', 'a').close()
    if not isfile('ANA/ana_config.json'):
        copyfile(join(harupexdir, 'ana_configtemplate.json'), 'ANA/ana_config.json')
    if not exists('ANA/intra/'):
        makedirs('ANA/intra/')#mapping, pages_pos,
    if not exists('toneo'):
        makedirs('toneo')#mapping, pages_pos,
    if not isfile(join('toneo','neo4j_config.json')):
        copyfile(join(harupexdir, 'neo4j_configtemplate.json'), join('toneo','neo4j_config.json'))
#TODO move_file in a subfolder, the L2P process should be adapted to


with open('workingdirectory', 'r') as dirfile:
    wd = dirfile.readline().rstrip()
setup_dir()
