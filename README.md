# Dépendances
- Python 3.4
- Neo4j > 2.x
- py2neo v3

## Optionnel mais recommandé:
treetagger developpés respectivement par le departement de Computational Linguistics de University of Stuttgart
wrapper python pour treetagger developpé par Laurent Pointal du CNRS LMSI

# Utilisation
Renseigner le répertoire de travail (contenant les fichiers texte à traiter) danw `workingdirectory`
- `python3 0Haruspex.py`
Modifier les fichiers de configuration `.yaml` générés dans le dossier du projet
- `python3 L2P_main.py`
- `python3 ANA_main.py`
- `python3 linking_main.py`

# Future Developpements:
## L2P:
-  permettre de réécrire/corriger/supprimer (superviser l'étape) les fiches.
-  proposer des options pour l'integration des footnotes en rawtextcontent.
-  proposer des options pour l'assemblage de documents en plusieurs txt4ana donc plusieurs sous-projets
-  permettre la gestion du corpus à l'utilisateur (concaténation par sous-ensembles, etc.)
## ANA:
-  permettre de récupérer les noms propres commençant par une majuscule en initialisation  
(complément au bootstrap while creating dict_occ_ref.)

## ANA POO:
