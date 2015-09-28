#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from py2neo import Graph, GraphError, Node, Relationship


class Source(object):

    def __init__(self, type_source, legende, filename=''):
        self.type_source = type_source
        self.filename = filename
        self.legende = legende
        self.node_type = "Source"

    def create_source(self, graph_db):

        # Ajouter propriétés du type "modified" ?
        if self.filename != '':
            source_properties = {'legende': self.legende, 'fichier': self.filename}
        else:
            source_properties = {'legende': self.legende}
        source_node = Node.cast(source_properties)
        source_node.labels.add(self.node_type)
        source_node.labels.add(self.type_source)
        self._node = source_node

        graph_db.create(self._node)

    def get_legende(self):
        return self.legende

    @property
    def node(self):
        return self._node
