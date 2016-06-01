#!/usr/bin/env python3
# encoding: utf-8
from py2neo import Node
from os.path import join
import math
import csv


class Page:
    def __init__(self, p_num):
        self.number = p_num
        self.atts = {}

    def upload(self, graph):
        n = graph.find_one("fiche", property_key = 'doc_position', property_value = self.number)
        if not n:
            n = Node("fiche", doc_position = self.number)
            graph.create(n)
        for new_att_name, new_att_value in self.atts.items():
            n[new_att_name] = new_att_value
            n.push()

class Keyword:
    ''' These are valid keyterm after moderation of the user'''
    def __init__(self, shape, wiki_shape, group, confidence, pages_list):
        self.shape = shape
        self.wiki_shape = wiki_shape
        self.group = group
        self.occ = 0#how many occ of this term in the whole coprus
        self.where = pages_list#points to a list of page objects ie  [page1, page1, page1, page2, page2, page3, page4, page4]
        self.in_pages = 0#in how many pages this keyterm is present?
        self.confidence = confidence#group confidence
        self.weight = 0.0
        self._calc_where()

    def _calc_where(self):
        self.in_pages = len(set(self.where))
        self.occ = len(self.where)

    def log_weight(self, tot_pages, factor):
        return math.pow(math.log10(nb_pages/self.in_pages), factor)

    def cos_weight(self, tot_pages, factor):
        return math.pow(math.cos((self.in_pages-2)/tot_pages), factor)#x-2 because under 2 pages with key there is no link... (so our 0 is translated to 2)

    def weightening(self, tot_pages, config):
        if config['keylinks']["term_weightening_mode"] == 'log':
            if config['keylinks']['term_weightening_factor'] == 'soft':
                factor = 1
            elif config['keylinks']['term_weightening_factor'].startswith('med'):
                factor = 2
            elif config['keylinks']['term_weightening_factor'] == 'hard':
                factor = 3
            elif isinstance(config['keylinks']['term_weightening_factor'], int):
                factor = config['keylinks']['term_weightening_factor']
            self.weight = self.log_weight(tot_pages, factor)
        elif config['keylinks']["term_weightening_mode"] == 'cos':
            if config['keylinks']['term_weightening_factor'] == 'soft':
                factor = 30
            elif config['keylinks']['term_weightening_factor'].startswith('med'):
                factor = 100
            elif config['keylinks']['term_weightening_factor'] == 'hard':
                factor = 500
            elif isinstance(config['keylinks']['term_weightening_factor'], int):
                factor = config['keylinks']['term_weightening_factor']
            self.weight = self.cos_weight(tot_pages, factor)

    def merge_with(self, withwho):
        #withwho is a keyword object
        self.where += withwho.where
        self._calc_where()



class Link:
    '''this is a global class for all the links'''
    def __init__(self, page_obj_s, page_obj_t):
        self.source = page_obj_s
        self.target = page_obj_t
        self.line = []# a line to be written in the csv
        self.ponderation = 0.0
        self.threshold_passed = True

    def scale_pond(self, minpond, maxpond):
        self.ponderation = (self.ponderation-minpond)/(maxpond - minpond)

    def test_threshold(self, config):
        '''
        to define various threshold, the most simple is based on the global ponderation
        this avoid having huge base with bilion of useless super weak links
        '''
        if self.ponderation < config['keylinks']['ponderation_threshold']:
            self.threshold_passed = False

    def write_line(self, csvwriter):
        #the haeder should have been written first (out the method)
        if self.threshold_passed:
            csvwriter.writerow(self.line)


class UniqueL(Link):
    '''UniqueL are unique links between two documents'''
    def __init__(self, kwargs):
        super().__init__(kwargs['page_obj_s'], kwargs['page_obj_t'])
        self.sublinks = set([kwargs['sublink']])#is a set of link objects
        self.quantity = 0#number of sublinks between 2 pages

    def calc_ponderation(self, config):
        for sublink in self.sublinks:
            self.quantity += 1
            if config['uniquelinks']['ponderation'] == 'sum':
                self.ponderation += sublink.ponderation
            elif config['uniquelinks']['ponderation'] == 'angle':
                pass#TODO calc this value and try to test the results
        if config['uniquelinks']['ponderation_mode'] == 'log':
            self.ponderation = math.log10(self.ponderation)

    def build_line(self):
        #build a specific line to be written in the csv
        self.line = [self.source.number, self.target.number, self.ponderation, self.quantity]


class KeywordL(Link):
    '''KeywordL are links based on co-occurrences of a keyword between two documents'''
    def __init__(self, kwargs):
        super().__init__(kwargs['page_obj_s'], kwargs['page_obj_t'])
        self.keyword = kwargs['keyword']#this points to a Keyword object
        self.occ_insource = kwargs['occ_insource']#integer, number of occurrence of the keyword in the source page
        self.occ_intarget = kwargs['occ_intarget']
        self.min_occ = -1

    def build_line(self):
        #write the haeder first
        self.line = [self.source.number, self.target.number, self.ponderation, self.keyword.shape, self.keyword.wiki_shape, self.keyword.group, self.keyword.confidence, self.keyword.occ, self.min_occ, self.occ_insource + self.occ_intarget]

    def _calc_pages_closeness(self, config):
        self.min_occ = min(self.occ_insource, self.occ_intarget)
        tf = self.occ_intarget + self.occ_insource
        if config['keylinks']['document_closeness_factor'] == 'verysoft':
            closeness = tf
        elif config['keylinks']['document_closeness_factor'] == 'soft':
            closeness = float(math.log10(tf*self.min_occ))
        if config['keylinks']['document_closeness_factor'].startswith('med'):
            closeness = float(math.log10(tf*math.pow(self.min_occ, 3)))
        if config['keylinks']['document_closeness_factor'] == 'hard':
            closeness = float(math.log10(tf*math.pow(self.min_occ, 8)))
        if config['keylinks']['document_closeness_factor'] == 'veryhard':
            closeness = float(math.log10(tf)*math.pow(self.min_occ, 2))
        return closeness

    def calc_ponderation(self, config):
        closeness = self._calc_pages_closeness(config)
        if config['keylinks']['ponderation_mode'] == 'log':
            self.ponderation = math.log10(closeness * self.keyword.weight)
        else:
            self.ponderation = closeness * self.keyword.weight
