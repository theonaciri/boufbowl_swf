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

- `contact_url` : Discord Dofus 3, avec une invitation issue de sa fiche Discord.
- `android_download_url` et `desktop_download_url` : URL HTTPS facultatives pour
  distribuer des builds depuis un autre hébergement.
- `tot_quote_source_url` : URL HTTPS à ajouter ultérieurement.

`GET /api/site` découvre les fichiers locaux et renvoie les liens effectivement
disponibles. Un fichier absent n’est pas présenté comme téléchargeable. Les
fichiers locaux servis sont exclusivement :

- `android/build/BoufbowlOffline.apk` → `/downloads/BoufbowlOffline.apk`.
- `linux/build/BoufbowlOffline-linux.tar.gz` → `/downloads/BoufbowlOffline-linux.tar.gz`.

Les chemins arbitraires et les liens symboliques sortant du dossier de build ne
sont pas accessibles. Les paquets sont des artefacts ignorés par Git. Le site
indique leur taille et les prérequis de la plateforme. Le téléchargement ne
nécessite aucun accès au dépôt GitHub privé.

Les constructeurs acceptent `--server-url https://adresse-du-serveur` pour
configurer le serveur distant : valeur par défaut du client Android et lanceur
`play-online.sh` de l’archive Linux. Reconstruire les builds si cette adresse
change. L’archive Linux x86-64 conserve aussi le lanceur local `play.sh`.
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

Les builds Android ARM64 et Linux x86-64 ont été produits avec l’adresse du serveur
actuelle. L’APK a été contrôlé avec `apksigner verify` (signatures v1 et v2),
`aapt dump badging` et une vérification de l’intégrité ZIP. Il cible Android 35,
requiert Android 23 minimum et contient le runtime ARM64. Aucune validation sur
un appareil physique n’a été effectuée lors de cette livraison.

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
sont exportées depuis `cutscene-boufbowler-repository.swf`, avec les classes et
la colorisation du client original, via `IllustrationViewFactory`. Les trois
poses sont vestiaire, victoire et face-à-face : 138 images au total. Les outils
et SWF temporaires de capture ne sont pas distribués. Les polices de l’atelier
sont celles intégrées au client, avec leurs métadonnées d’origine ; les polices
Barlow du reste de la page conservent leurs licences OFL.

La sélection de classe, de genre, de pose et de légende ne modifie aucune équipe
sur le serveur. Le nom saisi est un surnom local, non enregistré. Le bouton OK
ouvre un bilan et permet de préparer une proposition d’aide contextualisée.
La grille des états distingue dessins, corps animés et fidélité des couleurs.
La petite image de terrain est explicitement une référence Crâ, pas une preuve
que le corps d’une autre classe a été restauré.

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
d’ambiance. Un fichier manquant n’est jamais proposé à la lecture. Le studio
permet de rechercher et filtrer les bruitages, ambiances et voix. Les deux
ateliers partagent un lecteur unique et un oscillogramme des données audio
réelles ; aucun son ne démarre sans action. L’animation respecte la réduction
des mouvements et la commande générale de pause des animations.

Les téléchargements Desktop et Android sont mis en avant. La version Web est
identifiée comme expérimentale, lente, buguée et instable avec Ruffle. Un appel
à bénévoles dédié permet de proposer de l’aide sur la compatibilité Web.
