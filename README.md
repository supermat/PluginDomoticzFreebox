# Domoticz Freebox Plugin
Plugin Python Domoticz pour accéder au services de l'API V4 de la Freebox

## Fonctionnalités

* Création du token d'authentification lors du premier lancement (une validation est nécessaire sur l'écran de la Freebox serveur)
* Création d'un dispositif par partition de disque dur connecté à la Freebox (disques internes et externes)
* Création de 3 dispositifs pour suivre les températures de la Freebox
* Création d'un dispositif switch par adresse mac pour laquelle vérifier la présence ou non à proximité de la Freebox.

## Installation

Requis : Python version 3.4 or supérieur & Domoticz version 3.87xx ou supérieur.

* En ligne de commande aller dans le répertoire plugin de Domoticz (domoticz/plugins)
* Lancer la commande: ```git clone https://github.com/supermat/PluginDomoticzFreebox.git```
* Redemmarrer le service Domoticz en lancant la commande '''sudo /init.d/domoticz restart'''

## Updating

Pour mettre à jour le plugin :

* En ligne de commande aller dans le répertoire plugin de Domoticz (domoticz/plugins)
* Lancer la commande: ```git pull```
* Redemmarrer le service Domoticz en lancant la commande ```sudo /init.d/domoticz restart```

## Configuration

| Field | Information|
| ----- | ---------- |
| Address | L'adresse d'accès à la box avec le http(s) devant (http://mafreebox.free.fr sur réseau local)  |
| Port | Le port pour accéder à la Freebox (80 sur réseau local) |
| Token | Le Token de connexion à la Freebox qui vous sera donné lors de la première connexion du plugin (voir les log) |
| Liste mac adresse pour présence (séparé par ;) | Une liste d'adresse mac à vérifier sur les équipements enregistrés sur la Freebox comme étant présent à proximité de la box (reachable et active). Présent au domicile |
| Debug | Si true plus de log apparaitront dans la console de log |

Dans la partie Matériel de Domoticz, chercher 'Freebox Python Plugin'.
Laissez les valeur par defaut sur un réseau local, ou configurez votre adresse et port.
Ajoutez le Matériel et rendez vous dans les log.
Lors de la première utilisation, laissez le token vide.

Au démarrage, si le token n'est pas défini, le plugin en demander un à la Freebox, il vous faut alors vous déplacer jusqu'à l'écran de la Freebox pourrépondre oui, puis revenir sur votre Domoticz pour copier coller le token qui s'affiche dans la fenetre de log, dans la partie Token de confirguration du plugin.

Desactivez le plugin, autoriser l'ajout de nouveau dispositif pendant 5 minutes, puis réacivez le plugin pour le faire redemarrer.
Les dispositifs vont se créer.
A chaque démarrage du plugin, les dispositifs nouveaux ou maquant seront ajoutés.
Vous pouvez supprimer ceux qui ne vous interresse pas et inclure ceux qui vous interresse.

| Dispositifs | Description|
| ----- | ---------- |
| Système | Températures de la Freebox et du switch interne  |
| Disque | Pourcentage d'espace utilisé de chaque partition connectées à la Freebox au moment du démarrage du Plugin avec autorisation d'ajout de dispositifs |
| Présence | Pour chaque adresse mac renseignée, si elle est trouvée enregistrée sur la Freebox, un dispositif switch est créé, indiquant la presence (on) ou l'absence (off) du matériel à proximité de la box. Cela permet de tester la presence d'une personne au domicile en vérifiant la presence de sont smartphone par exemple. Cela fonctionne, même avec les Iphones |

Note : Un fichier ```devicemapping.json``` est créé pour garder l'association des infos de la Freebox avec le bon device créé au moment du démarrage du Plugin.

## Change log

| Version | Information|
| ----- | ---------- |
| 1.0 | Version initial : connexion (token), températures système, espace disque, présence |
