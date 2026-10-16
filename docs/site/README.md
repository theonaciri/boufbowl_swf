# Page d’accueil Boufbowl

La racine `/` sert `index.html`. Le jeu est désormais à `/play.html` ;
`/browser.html` redirige vers cette adresse, y compris pour les requêtes HEAD.
Les liens des pages juridiques sont régénérés vers `/play.html`.

La page en français présente le fan game indépendant et non affilié à ANKAMA
Games, son statut de restauration, ses fonctionnalités existantes, ses limites et
ses besoins en bénévoles. Le projet reste non commercial, sans publicité ni
achat de kamas. La citation transmise par le porteur du projet est identifiée
comme rapportée ; son URL source reste à renseigner.

## Configuration publique

`resources/site.json` configure les liens publics :

- `server_url` : serveur HTTPS utilisé par défaut par les packages Windows, Linux et Android.
  `--server-url` permet une surcharge explicite ; le packaging refuse une adresse absente.
- `contact_url` : Discord Dofus 3, avec une invitation issue de sa fiche Discord.
- `android_download_url`, `desktop_download_url` (Linux) et `windows_download_url` : URL HTTPS facultatives pour
  distribuer des builds depuis un autre hébergement.
- `tot_quote_source_url` : URL HTTPS à ajouter ultérieurement.

`GET /api/site` découvre les fichiers locaux et renvoie les liens effectivement
disponibles. Un fichier absent n’est pas présenté comme téléchargeable. Les
fichiers locaux servis sont exclusivement :

- `android/build/BoufbowlOffline.apk` → `/downloads/BoufbowlOffline.apk`.
- `linux/build/Boufbowl-linux.tar.gz` → `/downloads/Boufbowl-linux.tar.gz`.
- `windows/build/Boufbowl-windows.zip` → `/downloads/Boufbowl-windows.zip`.

Les chemins arbitraires et les liens symboliques sortant du dossier de build ne
sont pas accessibles. Les paquets sont des artefacts ignorés par Git. Le site
indique leur taille et les prérequis de la plateforme. Le téléchargement ne
nécessite aucun accès au dépôt GitHub privé.

Construire les paquets joueurs Desktop avec
`python3 -m tools.build_player_downloads --server-url https://adresse-du-serveur`.
Ils contiennent uniquement le lecteur Flash, les instructions et un lanceur :
`Jouer.cmd` sous Windows, `jouer.sh` sous Linux. Le jeu, les ressources et les
requêtes de compte sont chargés depuis le serveur distant. Ni Python, ni Bun,
ni base de données ou serveur local ne sont nécessaires chez les joueurs.
Wine avec prise en charge 32 bits reste nécessaire sous Linux ; Windows utilise
directement le lecteur fourni. Les tailles affichées proviennent des archives
réelles, indépendamment pour chaque plateforme. Le gros paquet hors ligne de
`linux/build.py` est réservé au développement et n’est plus proposé sur le site.
Le constructeur Android accepte également `--server-url` pour son serveur par
défaut. Reconstruire les paquets si cette adresse change.
Le certificat Android est conservé hors du dépôt dans le cache des outils.

## Interactions et accessibilité

Les ateliers des vestiaires changent de classe, de variante et de pose, puis
détaillent les ressources visuelles et sonores retrouvées (voir ci-dessous).
Le bouton de mêlée produit une onomatopée, sans lecture sonore automatique.
Les annonces textuelles utilisent une région accessible. Les fenêtres de vidéo
et de bénévolat sont des dialogues natifs avec fermeture par Échap ; la vidéo
s’arrête à la fermeture. La candidature est un message personnalisable à copier,
pas un formulaire qui transmet des données au serveur.

Le menu mobile expose son état. Les révélations au défilement et les animations
respectent `prefers-reduced-motion`, et une commande en pied de page les suspend.
Le contenu est visible sans JavaScript. Les polices Barlow sont locales, avec leurs
licences OFL. La page n’ajoute aucun cookie ou identifiant de suivi.

## Visuels et provenance

Référence d’ambiance et de composition : [Sanstour](https://sanstour.com/).
Ses illustrations et ses vidéos ne sont pas reprises.

Tous les visuels de la page proviennent du client original : aucune image générée
par IA n’est utilisée. Les captures `game-team.png`, `game-customization.png` et
`game-club.png` viennent de `evidence/`. Les captures des personnages spéciaux,
des ordres et de la résolution 3D sont prises dans le client via Ruffle.

Le carrousel présente les animations plein écran disponibles dans
`assets/artworks/cutscene-illustration.swf` : contacts élémentaires, lancer,
réceptions, interception, essai, tutoriel et réactions des tribunes. Les clips
H.264 muets et leurs affiches WebP sont capturés depuis les animations du client,
avec ses propres personnages et palettes. Les scènes de match utilisent les
fixtures de protocole du dépôt ; ce sont des démonstrations de restauration.
Les fichiers Flash et les données du serveur restent inchangés.

Le carrousel permet de naviguer avec les flèches, Début/Fin, les catégories et
les boutons précédent/suivant. Une commande de pause et un agrandissement plein
écran sont disponibles. Il suspend son défilement au survol et au focus ; les
vidéos se mettent en pause hors écran, en arrière-plan et avec les animations
suspendues. Avec `prefers-reduced-motion`, seules les affiches sont présentées.

`assets/site/tutorial-archive.mp4` est une conversion H.264/AAC de
`assets/videos/tutorial-intro.flv` (36 secondes). `tutorial-field.mp4` et
`tutorial-poster.webp` viennent de `layout_tuto_01.flv`. Ces archives sont
identifiées comme telles et ne constituent pas une vidéo de lancement.

La page `/play.html` utilise toute la largeur et toute la hauteur du viewport,
sans navigation ni pied de page juridique. Les textes juridiques restent
accessibles depuis la page d’accueil.

## Vérification

```sh
python3 -m unittest tests.test_homepage tests.test_browser_server -v
python3 -m tools.build_legal_pages --check
```

Les tests vérifient les routes de l’accueil, du jeu et de l’ancienne URL, la
découverte des builds et les limites de distribution des fichiers. La validation
visuelle et interactive se fait dans le navigateur, sur ordinateur et en largeur
mobile. Un APK compilé et signé ne remplace pas une validation sur appareil Android.


## Builds de test produits pour ce déploiement

Les builds Android ARM64, Windows et Linux x86-64 ont été produits avec l’adresse du serveur
actuelle. L’APK a été contrôlé avec `apksigner verify` (signatures v1 et v2),
`aapt dump badging` et une vérification de l’intégrité ZIP. Il cible Android 35,
requiert Android 23 minimum et contient le runtime ARM64. Aucune validation sur
un appareil physique n’a été effectuée lors de cette livraison.
Les archives Desktop et leurs liens ont été contrôlés ; l’exécution du nouveau
lanceur Windows n’a pas été testée sur une machine Windows dans cet environnement.

Pour ce serveur de compilation ARM, les outils Android 35 x86-64 ont été exécutés
avec QEMU et les bibliothèques amd64 de compilation croisée. Le chemin de l’outil
AAPT2 a été fourni à Gradle via `JAVA_TOOL_OPTIONS` et la propriété
`org.gradle.project.android.aapt2FromMavenOverride`. Ces dépendances restent hors
du dépôt ; l’APK distribué demeure une application Android ARM64 native AIR.

## Ateliers de restauration en HTML

`restoration.js` et `restoration.css` recréent le vestiaire, le sélecteur des
stades et un studio d’écoute, sans charger Ruffle. La capture de référence fournie
par le porteur du projet est conservée en WebP et peut être affichée en comparaison.
Les 14 icônes de classes et le petit aperçu Crâ sont découpés dans cette capture.
Les illustrations transparentes des 28 variantes classiques et des 18 légendes
sont réexportées dans les couleurs par défaut actuelles du client : première
palette de chaque classe, valeurs explicites par genre, palette dédiée des héros.
Aucun sélecteur Dofus/Wakfu n’est affiché. Les huit poses du vestiaire proviennent
de `cutscene-boufbowler-repository.swf` : les sept poses publiques et le groupe
alternatif `boufbowler1_posing_11` (accroupi). Dix poses supplémentaires proviennent
de `cutscene-illustration.swf` : lancer, plongeon, gros plan du ballon, acrobatie,
rotation, déséquilibre, envol, reprise acrobatique, esquive et tacle glissé.
Les libellés d’action décrivent visuellement les poses ; le manifeste conserve
les noms exacts des symboles Flash.

Chaque personnage dispose ainsi de 18 poses, soit 828 images. Le rendu utilise
les groupes d’illustration et la colorisation natifs du client, sans génération
d’image. Les vecteurs sont rendus au double de l’ancienne résolution : personnage
de 1 000 px de haut sur un canevas transparent de 1 080 px, contre 540 px auparavant.
Les ombres et effets qui font partie du dessin original sont conservés. Les WebP
sont encodés en qualité 92. Le script de capture utilise un tampon WebGL conservé
pour éviter les captures vides ; les très larges poses passent par l’encodeur PNG
du client. Les SWF temporaires de capture ne sont pas distribués.
Chaque pose conserve le symbole et le dessin de la bibliothèque originale ;
aucun dessin supplémentaire n’est inventé.

`tools/site_portrait_capture.as.inc` contient les callbacks d’export, injectés
uniquement dans un SWF distinct ; le client jouable n’est pas modifié.
`tools/site_portrait_capture.js` crée le lecteur d’export avec son tampon WebGL
conservé et restitue chaque PNG avec ses marges, sans dépendre du DPI de l’écran.
`python3 -m tools.site_portraits --plan` décrit les poses et couleurs à exporter.
`python3 -m tools.site_portraits` écrit `assets/site/restoration/portraits.json` ;
`--check` vérifie les exports, les dimensions et les empreintes des sources et des
palettes. Les URLs des images sont versionnées pour remplacer les anciens aperçus
en cache. Les polices de l’atelier
sont celles intégrées au client, avec leurs métadonnées d’origine ; les polices
Barlow du reste de la page conservent leurs licences OFL.

La sélection de classe, de genre, de pose et de légende ne modifie aucune équipe
sur le serveur. Le nom saisi est un surnom local, non enregistré. Le bouton OK
ouvre un bilan et permet de préparer une proposition d’aide contextualisée.
La grille des états distingue dessins, corps animés et fidélité des couleurs.
La petite image de terrain utilise les trois planches fournies par le projet :
Iop, Osamodas, Sacrieur, Sadida, Pandawa, Crâ, Eniripsa, Ecaflip, Sram, Féca,
Xélor et Enutrof, en versions féminine et masculine. Le cadrage et le miroir
horizontal sont appliqués dans le navigateur, sans retoucher les images sources.
Roublard et Zobal affichent une référence manquante. Les légendes montrent une
référence de leur classe, explicitement identifiée. Ces références visuelles ne
prouvent pas que les pièces animées des corps ont été restaurées.
Le logo `assets/site/logo.webp` et le fond `assets/site/splash.webp` sont également
ceux fournis par le projet, sans génération d’image.

L’inventaire se régénère avec :

```sh
python3 -m tools.build_restoration_data
python3 -m tools.build_restoration_data --check
python3 -m unittest tests.test_restoration_inventory -v
```

Il lit les skins, les configurations des stades, le manifeste sonore et les
références MP3 du client compilé. Il déduplique les alias, ajoute les fichiers
présents hors références et exclut les chemins sortant du dépôt. Le périmètre
est explicite : une présence sur disque ne prouve ni l’exhaustivité de l’archive,
ni la fidélité d’une restitution. L’heure/date du bilan n’est pas un pourcentage
éditorial de progression. Les couleurs restent à vérifier ; seuls cinq corps
classiques sont retrouvés. Les surfaces 2D des neuf terrains existent, tandis que
seule la géométrie originale de Cania est disponible. Les variantes de textures
ne sont pas présentées comme des décors 3D originaux.

La sélection des stades détaille les fichiers de tactique, de résolution et
d’ambiance. Un fichier manquant n’est jamais proposé à la lecture.
Le bilan global des ressources additionne les illustrations (18 poses par
personnage), les corps animés classiques et spéciaux, les fonds tactiques, les
décors 3D originaux et l’audio. Chaque famille affiche son numérateur et son
dénominateur ; les ressources manquantes sont incluses. Ce bilan porte sur le
périmètre recensé des ateliers, pas sur un nombre inconnu de fichiers perdus.
Le compteur audio global inclut les musiques présentes et manquantes, dédupliquées
entre les stades. Les trois boucles de résolution sont indiquées « Restauré,
qualité basse » ; elles restent à améliorer. Le studio hors musique
permet de rechercher et filtrer les bruitages, ambiances et voix. Les deux
ateliers partagent un lecteur unique et un oscillogramme des données audio
réelles ; aucun son ne démarre sans action. L’animation respecte la réduction
des mouvements et la commande générale de pause des animations.

Les téléchargements Desktop et Android sont mis en avant. La version Web est
identifiée comme expérimentale, lente, buguée et instable avec Ruffle. Un appel
à bénévoles dédié permet de proposer de l’aide sur la compatibilité Web.

### Build des portraits du site

Les 828 portraits sont des sorties de build ignorées par Git. Les sources Flash,
les palettes, les références fournies et les petits manifestes restent versionnés.
Aucun service de génération d’images n’est utilisé : Ruffle rend les 18 poses
natives de chaque personnage, dans ses couleurs par défaut, sur fond transparent
à 1080 px (personnage de 1000 px de haut).

Prérequis : Python 3, Java 17, FFDec 26.3.0, Bun et le
Chromium Playwright. Depuis la racine du dépôt :

```sh
bun install --cwd tools/website --frozen-lockfile
(cd tools/website && bunx playwright install --with-deps chromium)
python3 -m tools.build_website --ffdec /chemin/ffdec.jar
python3 -m tools.build_website --check
```

`JAVA`, `BUN` et `FFDEC_JAR` permettent de choisir les outils ; `--java` et
`--bun` acceptent aussi un chemin. Le premier build exporte tous les portraits et les 46 icônes cubiques originales
du client (28 variantes de classes et 18 légendes). Les icônes PNG transparentes
sont exportées à ×4 depuis les frames nommées `id_*` de `BoufbowlerCubeSprite`,
dans `assets/site/restoration/grid-icons/`, sans recoloration. Les portraits conservent la tenue bleue par défaut, avec
une exception d’export pour Evangelyne (508), dont la tenue est noire (`000000`). Elles servent au
sélecteur de personnages et aux raccourcis du vestiaire. Elles sont ignorées par
Git ; leur manifeste local vérifie la source et les empreintes des exports.
Les suivants réutilisent les fichiers dont les couleurs, sources, dimensions et
empreintes correspondent au manifeste ; `--force` impose un nouvel export.
Le build actualise ensuite `portraits.json` et `inventory.json`. Exécuter le build
avant de publier le site ou de lancer les contrôles qui vérifient ses images.
Le rendu utilise un SWF temporaire et un serveur HTTP local sur un port libre ;
il ne lance aucun serveur de jeu et ne modifie ni le client ni la base de données.
Les fichiers générés doivent être copiés sur l’hébergement avec le reste du site.

Pour réparer les exports d’un personnage sans reconstruire les autres :

```sh
python3 -m tools.build_website --ffdec /chemin/ffdec.jar --force --character hero-513
```

L’option `--character` est répétable. Chaque personnage forme un lot ; ses poses
sont traitées séquentiellement dans un lecteur isolé. `--jobs 1`, `--jobs 2`,
`--jobs 3` ou `--jobs 4` choisit le nombre de lecteurs indépendants. Le réglage
par défaut est **1**, le plus rapide lors du comparatif sur ce serveur à quatre
cœurs avec rendu graphique logiciel.
Ajouter `--pose default` limite la réparation aux aperçus du sélecteur ; cette
option est également répétable pour exporter plusieurs poses précises.

### Inventaire, livraison et durée du build

`python3 -m tools.build_website` effectue maintenant toute la préparation publique :

- vérification et export incrémental des portraits ;
- nouveau relevé des illustrations, corps, surfaces, géométries et sons, avec
  fichiers manquants, substitutions et restaurations audio de qualité basse ;
- calcul des totaux, ressources manquantes et pourcentages par famille et au global ;
- contrôle des médias, polices, images et clips utilisés par l’accueil ;
- génération des pages juridiques et disponibilité/taille réelle des téléchargements ;
- livraison de tous les fichiers publics dans `.local/website/dist`, avec
  `delivery.json` (liste, tailles et SHA-256) et rapport chronométré dans
  `.local/website/build-report.json`.

`--output /chemin/hors-du-depot/site` choisit une autre destination. Dans le
checkout, les destinations doivent rester sous `.local`. Le dossier est préparé
avant de remplacer la livraison précédente. Les fichiers supprimés des sources
ne restent pas dans la livraison. Les données privées, certificats, comptes,
bases SQLite et outils de compilation ne sont pas copiés.

Le dossier livré est un ensemble de fichiers publics à déployer sur le serveur
Boufbowl existant, avec les médias et téléchargements. Il ne remplace pas le
backend Python : les comptes et le jeu nécessitent toujours ses routes API.
La page d’accueil, ses ateliers et ses téléchargements peuvent être prévisualisés
sur un serveur statique grâce au manifeste public de repli. Aucun envoi ni
redémarrage du serveur n’est effectué par le build.

`--check` ne régénère rien : il contrôle les portraits, le relevé de restauration,
les pages juridiques, les téléchargements et les empreintes de la livraison.
Un ajout ou une suppression de ressource rend le contrôle périmé jusqu’au build
suivant. La progression affichée décrit les fichiers retrouvés dans le périmètre
recensé ; elle ne mesure pas une validation de fidélité au jeu original.

Chaque exécution affiche ses durées par étape, la mémoire maximale du navigateur
lorsqu’elle est mesurable sous Linux, puis une ligne finale `Total execution time`.
Le rapport complet se trouve dans `.local/website/build-report.json`. Les durées
mesurées du nouveau moteur et du build complet sont détaillées ci-dessous.

### Rendu optimisé et cache

Chaque lecteur charge les bibliothèques une seule fois. L’ActionScript prépare
les couleurs et le modèle du personnage une seule fois pour ses 18 poses. Il
retire l’interface du jeu du lecteur de capture. Avant chaque image, le build
vérifie un identifiant de requête unique, le label du personnage et la classe du
groupe d’animation natif, puis attend les cycles d’affichage nécessaires. Les
pauses arbitraires de 160/90 ms et l’attente initiale de trois secondes ont disparu.

Le navigateur encode directement les WebP transparents en qualité 0,92. Il envoie
les octets binaires au serveur de build : ni PNG/base64 sur le chemin normal, ni
sous-processus FFmpeg pour chaque image. Le lecteur est suspendu pendant
l’encodage et l’envoi, puis reprend pour la pose suivante. Le repli BitmapData/PNG
natif reste disponible pour une pose débordant de la scène ou un tampon GPU vide ;
son résultat est ensuite encodé en WebP dans le navigateur et vérifié.

La réutilisation est désormais fondée sur une empreinte **par portrait** : demande
exacte (pose, groupe, personnage et couleurs), sources Flash nécessaires, client,
configuration et code du rendu, version locale de Ruffle, dimensions et qualité.
Une modification du défaut de couleur d’un personnage invalide ses 18 poses ;
modifier une couleur inutilisée ne déclenche aucun export. Reconstruire le client
SWF ou changer le moteur invalide tous les portraits concernés. Le manifeste
vérifie aussi les dimensions et le SHA-256 du WebP existant. Les anciens exports
sans empreinte de rendu sont reconstruits une fois.

Le SWF de capture compilé est conservé sous `.local/website/capture/` et réutilisé
si ses sources et le compilateur sont identiques, y compris avec `--force`.
Chaque image terminée est enregistrée dans `.local/website/portrait-cache.json`.
Après interruption, relancer **sans `--force`** reprend uniquement les images
manquantes ou périmées. Si une source change pendant le build, celui-ci demande
une nouvelle exécution au lieu de valider des métadonnées incohérentes.

Pour comparer les réglages sur une autre machine :

```sh
python3 -m tools.benchmark_website --ffdec /chemin/ffdec.jar --java /chemin/java --bun /chemin/bun
```

Ce test force les mêmes 24 poses de six personnages avec un, deux et trois lecteurs,
contrôle la résolution et la réutilisation du modèle, et produit
`.local/website/benchmark-report.json`. Les configurations sont testées l’une après
l’autre ; elles ne doivent pas être lancées simultanément dans le même checkout.
Le nombre de lecteurs le plus rapide dépend de la machine et de son moteur graphique.

Mesures sur ce serveur à quatre cœurs (rendu logiciel, 16 octobre 2026), temps du
rendu incluant l’initialisation des lecteurs, hors compilation FFDec et livraison :

| Lecteurs | 24 poses | RSS cumulée du navigateur (pic) |
| --- | --- | --- |
| 1 | 21,93 s | 1 551 Mio |
| 2 | 27,48 s | 2 535 Mio |
| 3 | 38,66 s | 3 590 Mio |

Sur un autre échantillon identique de 18 poses, les optimisations d’encodage et de
suspension font passer le rendu d’un lecteur de **46,30 s à 22,58 s**. Trois
portraits de référence comparés entre les encodeurs ont une similarité SSIM
supérieure à 0,9997 et les mêmes dimensions. Les effets animés peuvent varier
légèrement entre captures ; le label du personnage et le groupe de pose doivent
rester strictement ceux demandés.

Les mesures et empreintes des sources sont conservées dans
`docs/site/portrait-benchmark.json`.

Le passage forcé complet des **828 portraits** a ensuite pris **10 min 27,35 s**,
inventaire et livraison compris, avec un lecteur et le SWF de capture compilé
déjà en cache. Le rendu seul a pris 624,69 s et la RSS cumulée du navigateur a
atteint 2 001 Mio. Les 46 modèles de personnages ont été initialisés une fois
chacun pour leurs 18 poses. Une première compilation du SWF ajoute son propre
coût ; l’installation des outils n’est pas comprise.

Le build suivant a réutilisé les **828 images**, avec **0 réexport**, et a pris
**1.85 s**, inventaire et livraison compris. Le contrôle fonctionne
aussi sans le cache local de portraits, à partir du manifeste livré.

Les propositions publiques de ressources et leur revue sont documentées dans
[CONTRIBUTIONS.md](CONTRIBUTIONS.md).

Les références individuelles « Sur le terrain » de Kriss, Ruel, Kabrok, Jack,
Goultard, Amalia et Roublard F sont les captures originales fournies dans
`assets/site/restoration/field-references/`. Elles priment sur la référence de
classe et sont orientées vers la gauche en CSS. Leur présence ne signifie pas
que les pièces du pantin animé ont été restaurées.
