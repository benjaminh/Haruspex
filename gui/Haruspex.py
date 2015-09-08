#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys, os, subprocess
import itertools
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt,QBasicTimer,pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor


class Haruspex(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initialize()

    def initialize(self):
        self.setWindowTitle('Haruspex')
        self.move(0, 0)

        self.create_menu()

        # Création du widget principal
        widget_p = QWidget(self)
        self.layout_p = QVBoxLayout()
        widget_p.setLayout(self.layout_p)
        self.setCentralWidget(widget_p)

        # Vue par onglets pour les différents modes
        self.tab_widget = QTabWidget()
        self.pre_ana_view = QWidget() # Mode 1
        self.ana_view = QWidget() # Mode 2
        self.ana_results_view = QWidget() # Mode 3
        self.ana_neo_view = QWidget() # Mode 4

        self.tab_widget.addTab(self.pre_ana_view, "Pré-traitement")
        self.tab_widget.addTab(self.ana_view, "ANA")
        self.tab_widget.addTab(self.ana_results_view, "Post-traitement")
        self.tab_widget.addTab(self.ana_neo_view, "Envoi vers Neo4j")

        self.layout_p.addWidget(self.tab_widget)

        # Initialisation des vues
        self.ana_window()
        self.post_ana_window()

        self.show()

    def create_menu(self):
        # Quitter l'application
        exitAction = QAction('Quitter',self)
        exitAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('Fichier')
        fileMenu.addAction(exitAction)

    ###############################################
    # Onglet de configuration et d'execution d'ANA
    ###############################################

    def ana_window(self):
        ana_window_layout = QVBoxLayout(self.ana_view)
        top_layout = QGridLayout()
        # Zone de saisie pour le bootstrap
        ana_bootstrap_label = QLabel('Saisissez de 1 à 5 mots représentatifs séparés par un \' ; \'', self)
        self.ana_bootstrap = QLineEdit()
        self.ana_bootstrap_button = QPushButton('Valider', self)
        bootstrap = self.ana_bootstrap.text()

        # Disposition des outils de sélection
        ana_directory_label = QLabel('Répertoire de travail d\'ANA', self)
        self.ana_directory_edit = QLineEdit()

        self.ana_directory = QPushButton('Parcourir', self)
        self.ana_directory.clicked.connect(self.ana_dir_open)

        self.ana_exec_button = QPushButton('Lancer ANA', self)

        self.ana_exec_button.clicked.connect(self.ana_exec)

        top_layout.addWidget(ana_directory_label, 0, 0)
        top_layout.addWidget(self.ana_directory_edit, 0, 2)
        top_layout.addWidget(self.ana_directory, 0, 1)

        top_layout.addWidget(ana_bootstrap_label, 1, 0)
        top_layout.addWidget(self.ana_bootstrap, 1, 1)
        top_layout.addWidget(self.ana_bootstrap_button, 1, 2)

        top_layout.addWidget(self.ana_exec_button, 2, 1)

        ana_window_layout.addLayout(top_layout)

    def ana_dir_open(self):
        self.ana_dir = QFileDialog.getExistingDirectory(self, 'Ouvrir un dossier')
        self.ana_directory_edit.setText(self.ana_dir)

    def ana_exec(self):
        ana_main = self.ana_dir
        ana_main_path = os.path.join(ana_main, 'ana_main.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(ana_main)
        subprocess.call(['python3', ana_main_path])
        os.chdir(origWD)

    ###############################################
    # Onglet de modération des résultats d'ANA
    ###############################################

    def post_ana_window(self):
        post_ana_layout = QVBoxLayout(self.ana_results_view)
        top_layout = QGridLayout()

        ana_output_label = QLabel('Fichier de résultats d\'ANA', self)
        self.ana_output_edit = QLineEdit()

        self.ana_output = QPushButton('Parcourir', self)
        self.ana_output.clicked.connect(self.ana_output_open)

        self.ana_display_button = QPushButton('Afficher les résultats', self)
        self.ana_display_button.clicked.connect(self.ana_display_results)


        top_layout.addWidget(ana_output_label, 0, 0)
        top_layout.addWidget(self.ana_output_edit, 0, 2)
        top_layout.addWidget(self.ana_output, 0, 1)
        top_layout.addWidget(self.ana_display_button, 1, 1)

        post_ana_layout.addLayout(top_layout)

    def ana_output_open(self):
        if hasattr(self, 'ana_dir'):
            # getOpenFileName retourne un tuple (fichier, filtre)
            self.ana_results, _ = QFileDialog.getOpenFileName(self, 'Ouvrir un fichier', self.ana_dir)
        else:
            self.ana_results, _ = QFileDialog.getOpenFileName(self, 'Ouvrir un fichier')
        self.ana_output_edit.setText(self.ana_results)


    def ana_display_results(self):
        # Créer une scroll area
        self.results_layout = QHBoxLayout()
        self.scroll = QScrollArea()
        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(6)

        # Création d'une fenêtre d'affichage du contexte
        self.keywordcontext = QTextEdit()
        self.keywordcontext.setReadOnly(True)

        filepath = self.ana_results
        if filepath:
            with open(filepath) as file:
                i = 0
                j = 0
                self.table.insertRow(self.table.rowCount())
                for line in itertools.islice(file, 3, None):
                    keyword = line.split(':')[1].rstrip('\n').strip()
                    keyword_box = QTableWidgetItem(keyword)
                    keyword_box.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                    keyword_box.setCheckState(Qt.Checked)
                    if j > 5 :
                        self.table.insertRow(i)
                        j = 0
                    self.table.setItem(i, j, keyword_box)
                    j += 1
                file.close()

                self.table.itemClicked.connect(self.handleItemClicked)
                self.table.itemPressed.connect(self.handleItemPressed)

                self.scroll.setWidget(self.table)
                self.scroll.setWidgetResizable(True)
                self.scroll.ensureWidgetVisible(self.table)

                self.results_layout.addWidget(self.scroll)
                self.results_layout.addWidget(self.keywordcontext)
                self.layout_p.addLayout(self.results_layout)

    def handleItemClicked(self, item):
        if item.checkState() == Qt.Unchecked:
            item.setBackground(QColor(100,100,150))
        else:
            item.setBackground(QColor(255,255,255))

    def handleItemPressed(self, item):
        print(item.text())
        self.keywordcontext.setText(item.text())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    haruspex = Haruspex()
    app.exec()
