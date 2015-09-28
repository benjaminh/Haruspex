#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from py2neo import Graph, GraphError, Node, Relationship
from Source import Source


class Fiche(object):

    '''Modèle de noeud relatif aux fiches descriptives
    La classe possède 4 méthodes pour créer des fiches
    et des relations entre fiches
    '''

    def __init__(self, tmp_id, titre, auteur,
                    contenu, date_creation, references):
        self.node_type = "Fiche_descriptive"
        self.tmp_id = tmp_id
        self.titre = titre
        self.auteur = auteur
        self.contenu = contenu
        self.date_creation = date_creation
        self.references = references

    def create_node(self,graph_db):
        # Ajouter propriétés du type "modified" ?
        fiche_properties = {'doc_position': self.tmp_id, 'titre': self.titre,
                            'auteur': self.auteur, 'contenu': self.contenu, 'date_creation': self.date_creation}
        fiche_node = Node.cast(fiche_properties)
        fiche_node.labels.add(self.node_type)
        self._node = fiche_node
        graph_db.create(self._node)

    def create_rel(self, graph_db, fiche_liee, complement, ponderation):
        rel = Relationship.cast(self.node, ("correle_a",
                                {"complement": complement,"ponderation": ponderation}), fiche_liee.node)
        graph_db.create(rel)

    def create_rel_recit(self, graph_db, fiche_liee, complement):
        rel = Relationship.cast(self.node, ("recit_lineaire",
                                {"complement": complement}), fiche_liee.node)
        graph_db.create(rel)

    def create_doc(self, graph_db, source, complement):
        rel = Relationship.cast(source.node, ("documente",
                                {"complement": complement}), self.node)
        graph_db.create(rel)

    def get_tmp_id(self):
        return self.tmp_id

    def get_titre(self):
        return self.titre

    def get_references(self):
        return self.references

    @property
    def node(self):
        return self._node
