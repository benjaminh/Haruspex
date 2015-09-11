# ANA

Implémentation Python du système ANA : Apprentissage Naturel Automatique

Le système ANA effectue automatiquement l'extraction de la terminologie d'un domaine et structure cet ensemble de concepts en un réseau sémantique. Cette acquisition de connaissances est fondée sur l'étude de textes libres. Le système n'utilise ni grammaire ni dictionnaire mais s'appuie sur des procédures statistiques, ce qui le rend indépendant de la langue utilisée dans les textes.

ANA est un outil développé en 1992 dans la thèse de C. Enguehard.

# Description du système

ANA effectue la découverte de nouveaux candidats `CAND` au sein d'un texte en utilisant différents fichiers nécessaires à l'induction de concepts:
- une liste de `mots fonctionnels`
- une liste de `mots liés`
- une liste de `mots de schéma`
- un `bootstrap`: une liste de concepts d'initialisation du processus de découverte de nouveaux mots clés

Le texte est découpé et étiqueté à partir des mots du `bootstrap`. Puis ANA génère une liste de fenêtres autour des `CAND` existants dont la taille est fixée (par exemple 2 mots autour du mot courant). Cette liste de fenêtres est ensuite utilisée pour l'induction de nouveaux concepts par l'analyse de critères de validité. L'induction de nouveaux concepts fonctionne en suivant 3 modes parallèles:
- `Expressions`
- `Expansions`
- `Simples` (notés Candidats dans le manuscrit original et dont le nom a été changé pour gagner en compréhension)

Puis le système effectue une destruction pour mettre à jour le bootstrap en supprimant les candidats dont la fréquence n'est plus suffisante. Enfin, le système réalise ces étapes de manière itérative jusqu'à atteindre un nombre d'étapes fixé par l'opérateur.

## Requis
module à installer
- regex [https://pypi.python.org/pypi/regex]
- distance [https://pypi.python.org/pypi/Distance/]

## Classes

4 classes principales d'objets composent le système ANA.

### Candidat

La classe Candidat comprend l'ensemble des termes identifiés dans le texte par ANA comme concepts représentatifs. Chaque candidat se voit associer sa liste de fenêtres dans le texte, sa fréquence d'apparition ainsi que les formes lexicales similaires. Les Candidats sont sélectionnés à partir de 3 mécanismes effectués de manière parallèle.

### Expression

La recherche d'`Expressions` (p.122) consiste à identifier des termes de la forme : `CAND1 (+ mot quelconque) + mot_schema + CAND`. Cette recherche se déroule en trois étapes:
- sélection des fenêtres valides
    * la taille de la fenêtre est fixée à 3 (la taille d'une fenêtre étant donnée par la somme des valeurs des termes inclus dans la fenêtre: un terme fonctionnel valant 0 et les autres valant 1).
    * une fenêtre est valide si elle comprend au moins deux concepts distincts dont l'un est en première position
- troncature des fenêtres sélectionnées:
    * les fenêtres valides sont tronquées après le second concepts (`CAND`). 
    * une liste de fenêtres valides et tronquées est alors créée pour chaque couple `CAND + mot_schema + CAND` dans le texte.
- identification de la morphologie la plus fréquente: toutes les formes (couples) dont la fréquence d'apparition est supérieur à un seuil `Sexp` (fixé à 3 par l'expérimentation') deviennent des candidats CAND

### Expansion

La recherche d'`Expansions` consiste à identifier des formes du type : `CAND + terme_quelconque`. La fenêtre a une taille fixée à 3. Les fenêtres étudiées sont donc du type `terme_quelconque + CAND + terme_quelconque`. Le processus se déroule en 2 étapes:
- sélection des fenêtres valides : une fenêtre est valide si elle comprend un unique `CAND`, que celui-ci est en une position définie (en l'occurrence au milieu) et qu'il n'y a pas de mot de schéma. Une liste de fenêtres valides dans le texte est alors créée pour chaque combinaison `CAND + terme_quelconque` ou `terme_quelconque + CAND`.
- identification de la morphologie du nouveau CAND : si la fréquence d'apparition de la combinaison est supérieure à un seuil (fixé à 3), elle devient `CAND`

### Simple

La recherche de `Simples` (p.134) consiste à identifier des `terme_quelconque` dans des formes du type : `CAND + mot_schema + terme_quelconque`. La fenêtre étudiée doit être de taille 3 au minimum. Le processus se déroule en trois étapes:
- - sélection des fenêtres valides
    * la taille de la fenêtre est fixée à 3 et produit des formes du type : `terme_quelconque + mot_stop + CAND + mot_schema + terme_quelconque` ou autres combinaisons (`mot_stop` n'étant pas compté dans la taille 3 de la fenêtre)
    * une fenêtre est valide si le `CAND` est en position 3, le `mot_schema` est en position 2 et si le symétrique de la fenêtre répond aussi à ces conditions.
- troncature des fenêtres sélectionnées: les fenêtres valides sont tronquées autour des portions de fenêtre comprenant `CAND`, `mot_schema` et `terme_quelconque`. Une liste de fenêtres valides et tronquées est alors créée pour `terme_quelconque`.
- identification de la morphologie la plus fréquente: le `Simple` peut se trouver dans différentes fenêtres possibles. En fonction des cas, différents seuils de validation existent:
    * si la fenêtre contient le même CAND avec le même mot_schema, alors le seuil de fréquence est de 3
    * si la fenêtre contient le même CAND avec des mot_schema différents, alors le seuil de fréquence est de 5
    * si la fenêtre contient des CAND différents avec le même mot_schema, alors le seuil de fréquence est de 5
    * si la fenêtre contient des CAND différents des mot_schema différents, alors le seuil de fréquence est de 10


## Les fichiers utiles: 
Les fichiers utiles sont: 
- `texte.txt`: le texte brut à analyser.
- `stop_list`: contient mot et groupe de mot très fréquente et non porteur de sens 
- `mots_schema`: contient les quelques forme de construction de mot-clef complexe ("de la", "du", "des", "de")
- `bootstrap`: contient quelques termes révélateurs du contenu global du texte. Au nombre de 4 environ. Pour amorcer la recherche. Ce sont des mots simples et avec un grand nombre d'occurence.
- `mots_interdits`: contient les mots qu'on ne veut pas voir apparaitre dans les résultats, mais qui peuvent permettre de contruire d'autres mots interessants (donc ne pas confondre avec la `stop_list`).

## Les fonctions utiles
Quelques fonctions outils qui seront appelées à divers endroit:
- `etiquette_texte`: Prend une énorme chaîne de mot (tout le texte), et retourne un énorme dictionnaire. On parlera du dico des étiquettes (numérotées). Une étiquette est composée d'un ou plusieurs mots consécutifs et son type. Il faut consommer tous les mots du texte. Types disponibles pour etiquette: la liste de tous les `CAND`, `mot_stop` (noté `stop`) ou `terme_quelconque` (noté `tq`). 
ex: 'les plus beaux bâtiments sont construits en béton armé' pourrait devenir `[[`les, `stop], [`plus, `stop], [`beaux, `tq], [`bâtiments, `BÂTIMENT], [`sont, `stop], [`en, `stop], [`béton armé, `BÉTON ARMÉ]]` (si 'béton armé' et 'batiment' sont écrits dans le fichier `bootstrap`).  
Cette fonction est lancée qu'une seule fois au début de ANA.  
Attention les indices ne correspondent plus aux indices des mots dans le texte d'origine lorsque des `CAND` composés de plusieurs mots sont captés (ça se décale).

- `egalite_souple_term`: Prend 2 termes et retourne un booléen. Permet de définir si 2 termes sont égaux, en calculant une proximité entre eux. Un seuil de flexibilité est défini. ex: 'bâtiments' et 'batiment' doit retourner VRAI. 
- `egalite_souple_chaine`: Prend 2 chaînes et retourne un booléen. Permet de définir si 2 chaînes sont égales. Retire les mots de la `stop_list` contenu dans les chaïnes. Calcul la sommes des proximités des paires de mots (chaine A, chaine B contiennent les paires A1 B1; A2 B2; A3 B3). ex: 'bâtiment construit en béton' et 'batiments construits avec du béton' deviennent 'bâtiment construit béton' et 'batiments construits béton'. Alors la fonction doit retourner VRAI. 
- `inclusion_souple`: Prend 2 chaînes et retourne un booléen. Retire les mots de la `stop_list` contenu dans les chaînes. Vérifie si la chaîne A est «~souplement incluse~» dans la chaîne B. Pour cela il faut trouver un mot dans B souplement égal au premier mot de A. Puis passer au mot suivant pour les deux chaines et vérifier l'égalité souple entre une seconde paire de mot (A2 B2). Ne trouve pas si les mots sont dans un autre ordre. ex: 'beau batiment' et 'les plus beaux bâtiments sont construits en béton' retourne VRAI.
- `defini_fenetres`: prend les paramètres: le dico des étiquettes, une liste de `CAND`, `W` (taille de la fenetre) et `w` (position du `CAND` dans la fenêtre (1, 2, 3 ou 4 souvent)) et sort une liste de toutes les suites d'étiquettes correspondant aux critères: ce sont les fenêtres. En fonction de la classe la fonction peut prendre une liste de tous les `CAND` en argument (pour `simple`), ou travailler candidat par candidat, donc ne prendre qu'un seul `CAND` en argument (pour `expression` et `expansion`).
- `change_etiquette`: Prend en argument, le dico des étiquettes, plusieurs indices (consécutifs) dans ce dico et un type, ne retourne rien. Concatène les chaînes de caractères contenues dans ces étiquettes. Modifie la première étiquette de la liste: remplace par la chaîne concaténée précédement et lui attribue le type donné en argument. Supprime les autres étiquettes de la liste.
Attention les indices dans la liste des étiquettes se décalent à chaque fois (supprime plusieurs item pour n'en insérer qu'un seul). 
- `fenetre_sans_v`: prend une fenetre d'étiquette et supprime tout les mots de la stoplist contenu dans cette fenetre. retourne une fenetre_sans_v (sans mots_schema). Pas pour opérer mais pour faire des vérification de fenetres valides



