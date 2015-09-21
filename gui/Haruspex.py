#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys, os, subprocess
import itertools
import json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QBasicTimer, pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor, QIntValidator


class Haruspex(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initialize()

    def initialize(self):
        self.setWindowTitle('Haruspex')
        self.move(0, 0)

        self.project_directory = ''
        self.ana_directory = ''

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
        self.pre_ana_window()
        self.ana_window()
        self.post_ana_window()
        self.ana_neo_window()

        self.show()

    def create_menu(self):
        # Quitter l'application
        exitAction = QAction('Quitter',self)
        exitAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('Fichier')
        fileMenu.addAction(exitAction)

    ###############################################
    # Onglet de pré-traitement
    ###############################################

    def pre_ana_window(self):

        self.tex_file = ''
        self.pict_folder = ''
        self.json_data = {}

        pre_ana_window_layout = QVBoxLayout(self.pre_ana_view)
        top_layout = QGridLayout()
        bottom_layout = QGridLayout()

        # Sélection du dossier à traiter
        project_dir_label = QLabel('Dossier du projet', self)
        project_dir_button = QPushButton('Parcourir', self)
        project_dir_button.clicked.connect(self.pre_ana_dir_open)
        self.project_dir_edit = QLineEdit()

        top_layout.addWidget(project_dir_label, 0, 0)
        top_layout.addWidget(self.project_dir_edit, 0, 1)
        top_layout.addWidget(project_dir_button, 0, 2)

        # Paramètres
        form_layout = QFormLayout()

        self.cut_paragraphs = QCheckBox()
        form_layout.addRow("&Découpe des paragraphes",self.cut_paragraphs)
        self.close_brackets = QCheckBox()
        form_layout.addRow("&Fermeture des crochets", self.close_brackets)
        self.sheet_min_size = QLineEdit()
        self.sheet_min_size.setPlaceholderText("150")
        size_validator = QIntValidator()
        self.sheet_min_size.setValidator(size_validator)
        form_layout.addRow("&Taille minimum des fiches (en mots)", self.sheet_min_size)
        self.word_after_last_sheet = QLineEdit()
        self.word_after_last_sheet.setPlaceholderText("Conclusion")
        form_layout.addRow("&Mot présent après la dernière fiche", self.word_after_last_sheet)
        self.author = QLineEdit()
        self.author.setPlaceholderText("Bertrand Dumas")
        form_layout.addRow("&Auteur", self.author)
        self.date_pub = QLineEdit()
        self.date_pub.setPlaceholderText("01/01/2000")
        form_layout.addRow("Date de publication", self.date_pub)

        validate_button = QPushButton('Enregistrer les paramètres', self)
        validate_button.clicked.connect(lambda: self.pre_ana_validate(self.project_dir_edit.text()))
        self.validate_label = QLabel('', self)
        latex2fiches_button = QPushButton('Créer le fichier', self)
        latex2fiches_button.clicked.connect(self.pre_ana)

        bottom_layout.addWidget(validate_button, 0, 0)
        bottom_layout.addWidget(self.validate_label, 0, 1)
        bottom_layout.addWidget(latex2fiches_button, 1, 0)

        pre_ana_window_layout.addLayout(top_layout)
        pre_ana_window_layout.addLayout(form_layout)
        pre_ana_window_layout.addLayout(bottom_layout)

    def pre_ana_dir_open(self):
        project_dir = QFileDialog.getExistingDirectory(self, 'Ouvrir un dossier')
        self.project_dir_edit.setText(project_dir)

        # Récupération du fichier .tex
        for dirpath, dirnames, files in os.walk(self.project_dir_edit.text()):
            for name in files:
                if name.lower().endswith(".tex"):
                    self.tex_file = os.path.join(dirpath, name)
            for dirname in dirnames:
                if dirname.lower().endswith("-img"):
                    self.pict_folder = dirname
        self.json_data.update({'project_path': self.project_dir_edit.text(), 'texfile_path': self.tex_file, 'pict_folder': self.pict_folder})

        self.project_directory = self.project_dir_edit.text()
        self.text4ana_edit.setText(self.project_directory+"/text4ana.txt")

    def pre_ana_validate(self, project_dir):
        with open(project_dir+"/L2P_config.json", "w") as outfile:
            params = {'last_word': self.word_after_last_sheet.text(),
            'author': self.author.text(),
            'publi_date': self.date_pub.text(),
            'paragraph_cut': self.cut_paragraphs.isChecked(),
            'close_squarebrackets': self.close_brackets.isChecked(),
            'mini_size': int(self.sheet_min_size.text())}
            self.json_data.update(params)
            json.dump(self.json_data, outfile, indent=4)
            self.validate_label.setText("Paramètres enregistrés")

    def pre_ana(self):
        pre_ana_dir = os.path.join(self.project_dir_edit.text(), os.pardir, "app/LaTeX2pages")
        pre_ana_main_path = os.path.join(pre_ana_dir, 'Latex2pages.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(pre_ana_dir)
        subprocess.call(['python3', pre_ana_main_path, self.project_dir_edit.text()])
        os.chdir(origWD)

    ###############################################
    # Onglet de configuration et d'execution d'ANA
    ###############################################

    def ana_window(self):
        ana_window_layout = QVBoxLayout(self.ana_view)
        top_layout = QHBoxLayout()
        form_layout = QFormLayout()
        self.ana_directory = os.path.join(os.getcwd(), "app/ANA")
        # Zone de saisie pour le bootstrap
        self.ana_bootstrap = QLineEdit()
        # Curseur de sélection des seuils pour la collecte ANA

        # Disposition des outils de sélection
        # TODO Modifier LaTeX2pages pour que text4ana.txt soit écrit dans le dossier du projet
        self.text4ana_edit = QLineEdit()

        ana_directory_label = QLabel('Répertoire de travail d\'ANA', self)
        self.ana_directory_edit = QLineEdit()
        self.ana_directory_edit.setText(self.ana_directory)
        self.ana_directory_button = QPushButton('Parcourir', self)
        self.ana_directory_button.clicked.connect(self.ana_dir_open)
        self.ana_loops = QLineEdit()
        loop_validator = QIntValidator()
        self.ana_loops.setValidator(loop_validator)


        # Définition des seuils
        self.ana_thresholds = QSlider(Qt.Horizontal)
        self.ana_thresholds.valueChanged.connect(self.ana_thresholds_slider)
        self.ana_thresholds.setMinimum(0)
        self.ana_thresholds.setMaximum(3)
        self.ana_thresholds_dict = {}
        #Bouton d'exécution
        self.ana_exec_button = QPushButton('Lancer ANA', self)
        self.ana_exec_button.clicked.connect(self.ana_exec)

        top_layout.addWidget(ana_directory_label)
        top_layout.addWidget(self.ana_directory_edit)
        top_layout.addWidget(self.ana_directory_button)

        form_layout.addRow('&Fichier à traiter', self.text4ana_edit)
        form_layout.addRow('&Saisissez de 1 à 5 mots représentatifs séparés par un \' ; \'', self.ana_bootstrap)
        form_layout.addRow('&Seuils', self.ana_thresholds)
        form_layout.addRow('&Nombre de passes', self.ana_loops)

        self.ana_validate_button = QPushButton('Enregistrer les paramètres', self)
        self.ana_validate_button.clicked.connect(lambda: self.ana_config_save(self.ana_bootstrap.text()))

        ana_window_layout.addLayout(top_layout)
        ana_window_layout.addLayout(form_layout)
        ana_window_layout.addWidget(self.ana_validate_button)
        ana_window_layout.addWidget(self.ana_exec_button)

    def ana_dir_open(self):
        self.ana_dir = QFileDialog.getExistingDirectory(self, 'Ouvrir un dossier')
        self.ana_directory_edit.setText(self.ana_dir)
        self.ana_directory = self.ana_directory_edit.text()

    def ana_thresholds_slider(self, value):
        # TODO redéfinir les 4 configs possibles
        if value == 0:
            self.ana_thresholds_dict.update(
            {"nucleus_nestedsteps": 3,
            "nucleus_threshold": [1,2,2,3],
            "expansion_threshold": 2,
            "expression_threshold": 2,
            "recession_threshold": 2
            })
        elif value == 1:
            self.ana_thresholds_dict.update(
            {"nucleus_nestedsteps": 3,
            "nucleus_threshold": [1,2,2,3],
            "expansion_threshold": 2,
            "expression_threshold": 2,
            "recession_threshold": 2
            })
        elif value == 2:
            self.ana_thresholds_dict.update(
            {"nucleus_nestedsteps": 3,
            "nucleus_threshold": [1,2,2,3],
            "expansion_threshold": 2,
            "expression_threshold": 2,
            "recession_threshold": 2
            })
        elif value == 3:
            self.ana_thresholds_dict.update(
            {"nucleus_nestedsteps": 3,
            "nucleus_threshold": [1,2,2,3],
            "expansion_threshold": 2,
            "expression_threshold": 2,
            "recession_threshold": 2
            })

    def ana_config_save(self, bootstrap):
        with open(self.project_directory+"/bootstrap", "w") as outfile:
            outfile.write(bootstrap)
            outfile.close()
        with open(self.project_directory+"/ana_config.json", "w") as outfile:
            self.ana_config_json = {"linkwords_file_path": self.ana_directory + "/french/schema",
            "stopword_file_path": self.ana_directory + "/french/stoplist_Fr.txt",
            "txt_file_path": self.project_directory + "/text4ana.txt",
            "bootstrap_file_path": "bootstrap",
            "global_steps": int(self.ana_loops.text())}
            self.ana_config_json.update(self.ana_thresholds_dict)
            json.dump(self.ana_config_json, outfile, indent=4)
            self.validate_label.setText("Paramètres enregistrés")
            outfile.close()

    def ana_exec(self):
        ana_main = self.ana_directory
        ana_main_path = os.path.join(ana_main, 'ana_main.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(ana_main)
        subprocess.call(['python3', ana_main_path, self.project_dir_edit.text()])
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
        top_layout.addWidget(self.ana_output_edit, 0, 1)
        top_layout.addWidget(self.ana_output, 0, 2)
        top_layout.addWidget(self.ana_display_button, 1, 1)

        post_ana_layout.addLayout(top_layout)


        # Créer une scroll area
        self.results_layout = QHBoxLayout()
        self.scroll = QScrollArea()
        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(6)


        # Création d'une fenêtre d'affichage du contexte
        self.keywordcontext = QTextEdit()
        self.keywordcontext.setReadOnly(True)

        self.results_layout.addWidget(self.scroll)
        self.results_layout.addWidget(self.keywordcontext)
        post_ana_layout.addLayout(self.results_layout)

    def ana_output_open(self):
        if hasattr(self, 'ana_dir'):
            # getOpenFileName retourne un tuple (fichier, filtre)
            self.ana_results, _ = QFileDialog.getOpenFileName(self, 'Ouvrir un fichier', self.ana_dir)
        else:
            self.ana_results, _ = QFileDialog.getOpenFileName(self, 'Ouvrir un fichier')
        self.ana_output_edit.setText(self.ana_results)


    def ana_display_results(self):

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

    def handleItemClicked(self, item):
        if item.checkState() == Qt.Unchecked:
            item.setBackground(QColor(100,100,150))
        else:
            item.setBackground(QColor(255,255,255))

    def handleItemPressed(self, item):
        print(item.text())
        self.keywordcontext.setText(item.text())

    ###############################################
    # Onglet de communication avec Neo4j
    ###############################################

    def ana_neo_window(self):
        print("nothing yet")
