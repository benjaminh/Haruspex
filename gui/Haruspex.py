#!/usr/bin/env python3
# encoding: utf-8


import sys, os, subprocess
import itertools
import json
import re
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QDate, Qt, QBasicTimer, pyqtSignal
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
        self.preANA_dir = 'preANA'

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
        self.odt_files = set()
        self.tex_files = set()
        self.tex_file = ''
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
        self.write_lastsection = QCheckBox()
        form_layout.addRow("&Écrire la dernière section?", self.write_lastsection)
        self.author = QLineEdit()
        self.author.setPlaceholderText("Bertrand Dumas")
        form_layout.addRow("&Auteur", self.author)
        self.calendar = QDateEdit(calendarPopup=True, displayFormat='MMMM yyyy', date=QDate.currentDate())
        self.date_pub = QDate.toString(self.calendar.date(), 'yyyy-MM-dd')
        form_layout.addRow("Date de publication", self.calendar)

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


    # silent conversion of odt file into minimal tex
    def writer2latex(self):
        # si pas de .tex mais .odt dans le dossier: silent conversion
        w2l_dir = os.path.join(self.project_dir_edit.text(), os.pardir, os.path.join('app','writer2latex'))
        origWD = os.getcwd() #remember original WorkingDirectory
        os.chdir(w2l_dir)
        for odt_file in self.odt_files:
            tex_name = re.sub(r'odt$', 'tex', odt_file)
            if os.path.isfile(tex_name):
                print('warning 2 files have the same name', odt_file, tex_name)
            else:
                arguments = ['-config', os.path.join('config', 'preANA.xml'), odt_file, os.path.join(self.preANA_dir, tex_name)]
                subprocess.call(['java', '-jar', 'writer2latex.jar'] + arguments)
                self.tex_files.add(os.path.join(self.preANA_dir, tex_name))

    def concatenate(self):
        concat_path = os.path.join(self.project_dir_edit.text(), os.path.join(self.preANA_dir,'concat.tex'))
        with open(concat_path, 'w') as concat_file:
            for tex_name in self.tex_files:
                with open(tex_name) as infile:
                    for line in infile:
                        concat_file.write(line)
        self.tex_file = concat_path

    def pre_ana_dir_open(self):
        project_dir = QFileDialog.getExistingDirectory(self, 'Ouvrir un dossier')
        self.project_dir_edit.setText(project_dir)
        self.project_directory = self.project_dir_edit.text()
        self.text4ana_edit.setText(os.path.join(self.project_directory, "text4ana.txt"))
        print(self.project_directory)
        if not os.path.exists(os.path.join(self.project_directory,'preANA')):
            os.mkdir(os.path.join(self.project_directory,'preANA'))

        # Récupération des fichiers d'entrée
        for dirpath, dirnames, files in os.walk(self.project_directory):
            for name in files:
                if name.lower().endswith(".tex"):
                    self.tex_files.add(os.path.join(dirpath, name))
                elif name.lower().endswith(".odt"):
                    self.odt_files.add(os.path.join(dirpath, name))
        if self.odt_files:# si .odt dans le dossier: silent conversion
            self.writer2latex()
        if len(self.tex_files) > 1:# concatene les fichiers tex en 1 seul fichier pour ana
            self.concatenate()
        else:
            self.tex_file = self.tex_files.pop()
        self.json_data.update({'project_path': self.project_directory, 'texfile_path': self.tex_file})
        self.ana_output_edit.setText(self.project_directory+"/output/context.json")

    def pre_ana_validate(self, project_dir):
        with open(project_dir+"/L2P_config.json", 'w', encoding = 'utf-8') as outfile:
            params = {'write_lastsection': self.write_lastsection.isChecked(),
            'author': self.author.text(),
            'publi_date': self.date_pub,
            'paragraph_cut': self.cut_paragraphs.isChecked(),
            'close_squarebrackets': self.close_brackets.isChecked(),
            'mini_size': int(self.sheet_min_size.text())}
            self.json_data.update(params)
            json.dump(self.json_data, outfile, ensure_ascii=False, indent=4)
            self.validate_label.setText("Paramètres enregistrés")

    def pre_ana(self):
        pre_ana_dir = os.path.join(self.project_directory, os.pardir, "app/LaTeX2pages")
        pre_ana_main_path = os.path.join(pre_ana_dir, 'Latex2pages.py')
        # origWD = os.getcwd() # remember our original working directory
        os.chdir(pre_ana_dir)
        subprocess.call(['python3', pre_ana_main_path, self.project_directory])
        # os.chdir(origWD)
        os.chdir(self.project_directory)

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
        self.text4ana_edit = QLineEdit()

        ana_directory_label = QLabel('Répertoire de travail d\'ANA', self)
        self.ana_directory_edit = QLineEdit()
        self.ana_directory_edit.setText(self.ana_directory)
        self.ana_directory_button = QPushButton('Parcourir', self)
        self.ana_directory_button.clicked.connect(self.ana_dir_open)
        self.ana_loops = QLineEdit()
        loop_validator = QIntValidator()
        self.ana_loops.setValidator(loop_validator)
        self.ana_autoloop = QCheckBox()

        # Définition des seuils
        self.ana_thresholds = QSlider(Qt.Horizontal)
        self.ana_thresholds.valueChanged.connect(self.ana_thresholds_slider)
        self.ana_thresholds.setMinimum(0)
        self.ana_thresholds.setMaximum(5)
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
        form_layout.addRow("&Nombre de passes automatique", self.ana_autoloop)
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
        with open(self.ana_directory+"/threshold_levels.json", 'r') as outfile:
            threshold_reference = json.loads(outfile.read())
            if value == 0:
                picked_thresholds = threshold_reference["threshold_verylow"]
            elif value == 1:
                picked_thresholds = threshold_reference["threshold_low"]
            elif value == 2:
                picked_thresholds = threshold_reference["threshold_med1"]
            elif value == 3:
                picked_thresholds = threshold_reference["threshold_med2"]
            elif value == 4:
                picked_thresholds = threshold_reference["threshold_high"]
            elif value == 5:
                picked_thresholds = threshold_reference["threshold_veryhigh"]
            picked_thresholds["nucleus_nestedsteps"] = 3
            self.ana_thresholds_dict.update(picked_thresholds)

    def ana_config_save(self, bootstrap):
        print('PROJET', self.project_directory, '\nself.text4ana_edit.text()', self.text4ana_edit.text())
        if not self.project_directory:
            self.project_directory = os.path.dirname(self.text4ana_edit.text())
        print('PROJET', self.project_directory, '\nself.text4ana_edit.text()', self.text4ana_edit.text())
        with open(self.project_directory+"/bootstrap", "w", encoding = 'utf8') as outfile:
            outfile.write(bootstrap)
            outfile.close()
        with open(self.project_directory+"/ana_config.json", "w", encoding = 'utf8') as outfile:
            if self.ana_autoloop.isChecked():
                analoops = 0
            else:
                analoops = int(self.ana_loops.text())
            self.ana_config_json = {"linkwords_file_path": self.ana_directory + "/french/schema",
            "stopword_file_path": self.ana_directory + "/french/stoplist_Fr.txt",
            # "txt_file_path": self.project_directory + "/text4ana.txt",
            "txt_file_path": self.text4ana_edit.text(),
            "bootstrap_file_path": self.project_directory+"/bootstrap",
            "automaticsteps": self.ana_autoloop.isChecked(),
            "global_steps": analoops}
            self.ana_config_json.update(self.ana_thresholds_dict)
            json.dump(self.ana_config_json, outfile, ensure_ascii=False, indent=4)
            self.validate_label.setText("Paramètres enregistrés")
            outfile.close()

    def ana_exec(self):
        ana_main = self.ana_directory
        ana_main_path = os.path.join(ana_main, 'ana_main.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(ana_main)
        subprocess.call(['python3', ana_main_path, self.project_directory])
        os.chdir(origWD)

    ###############################################
    # Onglet de modération des résultats d'ANA
    ###############################################

    def post_ana_window(self):
        post_ana_layout = QVBoxLayout(self.ana_results_view)
        top_layout = QGridLayout()
        bottom_layout = QGridLayout()
        self.ana_results = ''

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

        # Bouton d'enregistrement
        self.ana_results_add_keyword = QLineEdit()
        self.ana_results_add_keyword.setPlaceholderText("mot-cle-1; mot-cle-2; etc.")
        self.ana_results_save_button = QPushButton('Enregistrer', self)
        self.ana_results_save_button.clicked.connect(self.ana_results_save)
        self.ana_results_saved = QLabel(self)

        # Bouton d'exécution de ana_post_processing
        self.ana_post_process_exec = QPushButton('Terminer', self)
        self.ana_post_process_exec.clicked.connect(self.ana_post_processing)
        self.ana_post_process_label = QLabel(self)
        self.ana_post_process_label.setText('Valider les changements')

        self.results_layout.addWidget(self.scroll)
        self.results_layout.addWidget(self.keywordcontext)
        bottom_layout.addWidget(self.ana_results_save_button, 0, 1)
        bottom_layout.addWidget(self.ana_results_add_keyword, 0, 0)
        bottom_layout.addWidget(self.ana_results_saved, 0, 2)
        bottom_layout.addWidget(self.ana_post_process_exec, 1, 0)
        bottom_layout.addWidget(self.ana_post_process_label, 1, 1, 1, 2)
        post_ana_layout.addLayout(self.results_layout)
        post_ana_layout.addLayout(bottom_layout)

    def ana_output_open(self):
        if hasattr(self, 'ana_dir'):
            # getOpenFileName retourne un tuple (fichier, filtre)
            self.ana_results, _ = QFileDialog.getOpenFileName(self, 'Ouvrir un fichier', self.ana_dir)
        else:
            self.ana_results, _ = QFileDialog.getOpenFileName(self, 'Ouvrir un fichier')
        self.ana_output_edit.setText(self.ana_results)


    def ana_display_results(self):
        self.equivalence_table = {}
        if self.ana_results != '':
            filepath = self.ana_results
        else:
            filepath = self.ana_output_edit.text()

        if filepath:
            with open(filepath) as file:
                self.data = json.load(file)
                i = 0
                j = 0
                self.table.insertRow(self.table.rowCount())
                for key, value in sorted(self.data.items()):
                    keyword_box = QTableWidgetItem(key)
                    keyword_box.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                    keyword_box.setCheckState(Qt.Checked)
                    if j > 5 :
                        i += 1
                        self.table.insertRow(i)
                        j = 0
                    self.table.setItem(i, j, keyword_box)
                    equiv_key = '('+str(i)+','+str(j)+')'
                    self.equivalence_table[equiv_key] = key
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
        item_row = item.row()
        item_column = item.column()
        equiv_key = '('+str(item_row)+','+str(item_column)+')'
        key = self.equivalence_table[equiv_key]
        html_text = '<h1>'+item.text()+'</h1>'
        for sentence in self.data[key]:
            html_text += '<p>'+sentence+'</p>'
        self.keywordcontext.setHtml(html_text)

    def ana_results_save(self):
        self.table.selectAll()
        items = self.table.selectedItems()
        deleted_keywords = {}
        modified_keywords = {}
        new_keywords = {}
        #TODO gérer la modification du texte
        for item in items:
            item_row = item.row()
            item_column = item.column()
            equiv_key = '('+str(item_row)+','+str(item_column)+')'
            key = self.equivalence_table[equiv_key]
            if item.checkState() == Qt.Unchecked:
                # Mots-clés décochés
                deleted_keywords[key] = {'modification':'supprime'}
            elif item.checkState() == Qt.Checked and item.text() != key:
                #Mots-cles modifiés
                modified_keywords[key] = {'modification':'modifie', 'nouveau_mot_cle':item.text()}

        added_keywords = self.ana_results_add_keyword.text().split(';')
        for new_keyword in added_keywords:
            new_keywords[new_keyword.strip()] = {'modification':'ajoute'}
        modified_keywords.update(deleted_keywords)
        modified_keywords.update(new_keywords)

        with open(self.project_directory+"/output/modified_keywords.json", 'w', encoding = 'utf8') as outfile:
            json.dump(modified_keywords, outfile, ensure_ascii=False, indent=4)
            outfile.close()
        self.ana_results_saved.setText('Résultats sauvegardés')

    def ana_post_processing(self):
        ana_main_path = self.ana_directory
        ana_post_proc_path = os.path.join(ana_main_path, 'ana_postprocessing.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(ana_main_path)
        subprocess.call(['python3', ana_post_proc_path, self.project_directory])
        os.chdir(origWD)

    ###############################################
    # Onglet de communication avec Neo4j
    ###############################################

    def ana_neo_window(self):
        ana_neo_layout = QVBoxLayout(self.ana_neo_view)
        top_layout = QGridLayout()

        self.ana_preneo_exec = QPushButton('Lancer', self)
        self.ana_preneo_exec.clicked.connect(self.ana_preneo)
        self.ana_preneo_label = QLabel(self)
        self.ana_preneo_label.setText('Générer les liens entre fiches')
        self.ana_preneo_done_label = QLabel(self)

        self.ana_toneo_exec = QPushButton('Executer', self)
        self.ana_toneo_exec.clicked.connect(self.ana_toneo)
        self.ana_toneo_label = QLabel(self)
        self.ana_toneo_label.setText('Générer le graphe')
        self.ana_toneo_done_label = QLabel(self)

        top_layout.addWidget(self.ana_preneo_exec, 0, 1)
        top_layout.addWidget(self.ana_preneo_label, 0, 0)
        top_layout.addWidget(self.ana_preneo_done_label, 1, 0, 1, 2)

        top_layout.addWidget(self.ana_toneo_exec, 2, 1)
        top_layout.addWidget(self.ana_toneo_label, 2, 0)
        top_layout.addWidget(self.ana_toneo_done_label, 3, 0, 1, 2)

        ana_neo_layout.addLayout(top_layout)

    def ana_preneo(self):
        preneo_dir = os.path.join(self.ana_directory, os.pardir, "toneo")
        preneo_dir_path = os.path.join(preneo_dir, 'toneo.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(preneo_dir)
        subprocess.call(['python3', preneo_dir_path, self.project_directory])
        os.chdir(origWD)
        self.ana_preneo_done_label.setText('Liens générés')

    def ana_toneo(self):
        toneo_dir = os.path.join(self.ana_directory, os.pardir, "toneo")
        nodes_dir_path = os.path.join(toneo_dir, 'create_nodes.py')
        edges_dir_path = os.path.join(toneo_dir, 'create_edges.py')
        origWD = os.getcwd() # remember our original working directory
        os.chdir(toneo_dir)
        nodes_process = subprocess.Popen(['python3', nodes_dir_path, self.project_directory])
        nodes_process.communicate()
        edges_process = subprocess.Popen(['python3', edges_dir_path, self.project_directory])
        edges_process.communicate()
        os.chdir(origWD)
        self.ana_toneo_done_label.setText('Graphe généré')
