# Domoticz Freebox Plugin

Le Plugin "Freebox API" permet de piloter votre Freebox depuis votre serveur Domoticz.

**L'objectif est de continuer à faire vivre et enrichir le développement initialement proposé par supermat (mais qu'il ne maintient plus suite à son déménagement)**

**_Remarque importantes_ :**

 **- Si vous utilisiez le plugin initialement proposé par supermat, il sera nécessaire de supprimer la version  "matiériel" ainsi que le dossier "PluginDomoticzFreebox)" avant de poursuivre...**

 **- Le plugin proposé a été testé dans un nombre limité de cas. Il peut comporter des "bugs" (merci dans ce cas de me le remonter). Il est fournis sans garentie.**

## Fonctionnalités

* Création du token d'authentification lors du premier lancement (une validation est nécessaire via l'écran tactile du Freebox serveur)
* Création d'un dispositif par partition (disques internes et externes) affichant son taux d'occupation
* Création de dispositifs remontant l'ensemble des sondes de températures de la Freebox
* Création d'un dispositif de type switch permettant de superviser la disponibilité d'un équipement connecté à la Freebox (via son adresse mac). Ainsi il est possible de déduire la présence d'une personne au domicile (via la supervision de son smartphone).
* Création d'un dispositif switch de suivi et modification de l'état du wifi (actif/inactif)
* Création d'un dispositif switch permettant le redémarrage du Freebox serveur
* Création d'un dispositif switch d'état de la connexion Internet (WAN)
* Création de deux dispositifs pour le suivi du debit montant et descendant (en Ko/s)
* Création d'un dispositif switch  pour suivre l’état ou activer/désactiver l’alarme (uniquement en option sur Freebox Delta)

## Installation

Requis : Python version 3.8 or supérieur & Domoticz version 2022.1 ou supérieur.

* En ligne de commande aller dans le répertoire plugin de Domoticz (domoticz/plugins)
* Lancer la commande: ```git clone https://github.com/ilionel/PluginDomoticzFreebox.git```
* Redemmarrer le service Domoticz via la commande ```sudo service domoticz restart```

## Updating

Pour mettre à jour le plugin :

* En ligne de commande aller dans le répertoire des plugins de Domoticz (domoticz/plugins)
* Lancer la commande: ```git pull```
* Redemmarrer le service Domoticz via la commande ```sudo service domoticz restart```

## Configuration

| Field | Information|
| ----- | ---------- |
| URL | L'adresse d'accès à la Freebox (typiquement "https://mafreebox.freebox.fr") |
| Port | Le port pour accéder à l'interface Web de la Freebox (généralement "443" pour de https en réseau local) |
| Token | Le « Token » de connexion à la Freebox qui vous sera communiqué lors de la première connexion du plugin (et visible dans les logs de Domoticz) |
| Liste @mac pour la présence (séparé par ;) | La liste d'adresse mac dont vous souhaitez monitorer la disponibilité (quand elles sont connectées à la Freebox) |
| Option Debug | Pour obtenir des logs « très » détaillés (visible dans les journaux de Domoticz) |

Depuis le menu « Matériel » de Domoticz :
 - Chercher 'Freebox (via API)'
 - Laisser les valeurs par défaut, si votre serveur Domoticz est en un réseau local, ou sinon paramétrer l’adresse et port réseau de votre Freebox.
 - Ajouter le Matériel puis consulter les journaux de logs (depuis le menu Paramètre de Domoticz).

Note : Lors de la première utilisation le champ « Token » doit rester vide.

Au démarrage du plugin, si aucun token n’est renseigné, le plugin va s’enregistrer auprès de la Freebox. Vous devrez alors valider la demande directement depuis l’écran de votre box.  Après avoir répondu « oui » (il faudra vous déplacer jusqu’à votre Freebox), vous devrez « copier » (puis coller) le token qui s'affichera dans les logs du serveur Domoticz.
Ce token sera à « coller » dans le champ « Token » de la configuration du plugin.

Enfin, pour créer les dispositifs il faudra:
- Désactiver le plugin
- Autoriser l'ajout de nouveau dispositif pendant 5 minutes
- Réactiver le plugin

A chaque démarrage du plugin, les dispositifs nouveaux ou maquants seront ajoutés.
Vous pouvez choisir d’inclure ou non ces dispositifs à depuis l'interface dediée.

| Dispositifs | Description|
| ----- | ---------- |
| Système | Remontées des températures des sondes internes à la Freebox |
| Disque | Affichage du taux d'occupation (en %) de chaque partitions du/des disque(s) connecté(s) à la Freebox |
| Présence | Test la présence d'un équipement. Pour chaque adresse mac renseignée, si celle-ci est joignable par la Freebox, un dispositif de type Switch sera créé. Il indiquera la disponibilité (on) ou l'absence (off) de l'équipement. Cela permet de déduire la présence d'une personne au domicile en testant (par exemple) la présence de sont smartphone. |
| Alarme | Dispositif de type Switch permettant de voir l'état de l'alarme (active/inactive) et de piloter son activation/désactivation |
| Wifi | Affichage du statut du wifi (actif/inactif) et Switch permettant de modifier l'état (activation/désactivation) |
| Reboot | Switch permettant le redémarrage de la Freebox |
| WANStatus | État de la connexion Internet |
| Debits | Débits montants et descendants en Ko/s |

IMPORTANT : Pour piloter le wifi, le redémarrage de la box, gérer le player ou l'alarme, il est nécessaire d'accorder des droits spécifiques au plugin. Effectivement après l'inscription, le plugin n'aura que de simples droits de consultations.
Les droits de modification devront être positionnés manuellement via l'interface Freebox OS (depuis un navigateur http://mafreebox.freebox.fr) : menu "Paramètres de la Freebox" > "Gestion des accès" > "onglet Applications", sélectionner le plugin Domoticz puis cocher :
- "Modifications des réglages de la Freebox" (pour permettre la gestion du wifi ou le redémarrage de la box)
- "Gestion de l'alarme et maison connectée" (pour permettre la gestion de l'alarme "Freebox Delta")
- "Contrôle du Freebox Player" (pour mettre la supervision du player TV)

Note : Un fichier ```devicemapping.json``` est créé pour garder l'association des infos de la Freebox avec le bon device créé au moment du démarrage du Plugin.

## Change log

| Version | Information|
| ----- | ---------- |
| 1.0 | Version initial : connexion (token), températures système, espace disque, présence (https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz/)|
| 1.1 | Ajout des switch « WIFI » et « Reboot ». Ajout d'une pause au démarrage du plugin pour corriger certains pb |
| 1.1.1 | Prise en compte de l'adresse MAC en Majuscule ou minuscule pour la présence |
| 1.1.2 | Prise en compte de la Freebox mini 4K (qui n'a pas de disque interne) en conservant l'usage des disques externes |
| 1.1.3 | Prise en compte de la Freebox POP pour les températures (slallemand) et Ajout des détails de connection debits montants et descendant en Ko/s (chupi33 et les tests des ViaudJV) |
| 1.2.0 | Reprise et refonte du code pour un meilleur respect des standards de programmations Python |
| 1.3.0 | Intégration de l'option alarme de la FreeBox Delta (sur base du développement proposé par nachonam) |
| 1.4.0 | Ajout du support d'HTTPS/TLS (chiffrement des communications) |
| 1.5.0 | Integration _*Expérimentale*_ du player TV (supervision de l’état allumé/éteint) |
| 2.0.0 | Passage à l'API v8 + correctifs (sondes températures, alarme, disque...) |
| 2.1.0 | Amélioration de la robustesse du code suite au passage en 2.0 |
| 2.1.1 | Possibilitée de paramétrer la fréquence de rafraîchissement des valeurs |
| 2.1.2 | Possibilité d'éteindre le Player via Domoticz |
