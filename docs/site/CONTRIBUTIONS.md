# Contributions aux ressources de restauration

Le catalogue public `/api/asset-catalog` est une liste autorisée issue de
l’inventaire du build. Seuls les fichiers manquants, les substituts et les trois
musiques explicitement marquées « qualité basse » peuvent recevoir une proposition.
Le serveur détermine le chemin et le nom : aucun chemin de destination n’est
fourni par le visiteur. Le nom est strictement comparé, casse comprise. Les
extensions sont MP3, PNG, WebP, SWF/SWL et COLLADA/DAE selon la ressource attendue.

Chaque envoi requiert un jeton à usage unique lié à la ressource et à l’empreinte
réseau, valable dix minutes. Le serveur vérifie l’origine, impose un en-tête
personnalisé et ne permet pas CORS. Il refuse les corps sans longueur fixe,
les longueurs multiples et les transferts HTTP chunked. Une pause de dix secondes
ou un transfert dépassant deux minutes interrompt la réception.

## Limites

- MP3 : 20 Mio, quinze minutes, une piste audio MP3 mono/stéréo sans pièce jointe.
- Autres formats : 8 Mio. Images statiques limitées à 8 192 px par côté et 40 mégapixels.
- SWF : FWS ou CWS ; SWL : enveloppe Ankama L0 contenant FWS ou CWS, décompression bornée à 32 Mio ; imports externes et
  références à certaines capacités réseau/fichiers/ExternalInterface refusés.
- DAE : pas de DTD, d’entité XML, de référence réseau ni de chemin sortant des
  assets ; 100 000 éléments au maximum, aperçu limité à 3 000 points.
- Dix envois par heure et trente par jour par empreinte réseau ; cent par jour
  pour le serveur, huit traitements simultanément en réception/attente/analyse,
  trois propositions actives pour un même asset.
- Quarantaine limitée à 512 Mio avec une marge réservée aux analyses et aperçus.
  Jetons limités à trente par heure par empreinte et cinq cents sur le serveur.

## Antivirus et isolation

Installer `clamav`, `clamav-freshclam`, `bubblewrap`, `util-linux` (prlimit) et
`ffmpeg` (ffprobe compris). Garder le service FreshClam actif. Les signatures
sont lues dans `/var/lib/clamav` ; le build serveur actuel utilise ClamAV 1.5.4.
Une base daily de plus de 72 heures ou un scanner indisponible bloque les
prévisualisations et l’approbation. Aucun bouton administrateur ne permet de
contourner un échec de contrôle.

Le scanner et les décodeurs tournent dans Bubblewrap avec espaces de noms séparés,
sans réseau, sans accès à la base du jeu ni aux autres fichiers du projet. Seuls
les bibliothèques système en lecture seule, le fichier à contrôler et son dossier
privé d’aperçu sont montés. CPU, mémoire, fichiers et durée des processus sont
limités. Le worker d’analyse est unique ; les scans ne gardent pas le verrou de
la base du jeu. Le SWF décompressé est également analysé.

Les aperçus PNG/WAV sont recréés après contrôle, sans métadonnées utilisateur.
Le WAV est limité aux trente premières secondes. Les DAE montrent uniquement un
nuage de positions validées. Les fichiers Flash ne sont jamais exécutés : leur
aperçu décrit version, images, tags et labels, avec jusqu’à quatre éléments
statiques exportés en PNG par FFDec isolé si cet outil est installé. Le contrôle antivirus complète la
revue humaine ; il ne certifie pas la fidélité d’un asset au jeu original.

## Revue et intégration

`/assets-admin.html` utilise les sessions existantes. Le rôle **admin** est requis,
y compris pour chaque récupération d’aperçu et de fichier ; modérateur ne suffit
pas. Le menu commun relie cette page aux autres pages d’administration.

Les fichiers sont conservés sous `asset-contributions/` à côté de la base du
serveur, hors des chemins publics, avec leur propre base SQLite. La base des
comptes et sa version de schéma ne changent pas. Les décisions et leur auteur
sont journalisés. Un fichier infecté ou invalide est supprimé ; une erreur
technique de scan permet une nouvelle analyse. Un envoi en attente expire après
quatorze jours, un rejet supprime immédiatement les octets. Les empreintes réseau
des contributions sont effacées après trente jours. Un fichier approuvé reste
privé jusqu’à son intégration ou son rejet, dans la limite du stockage.

L’administrateur examine, approuve ou rejette. Approuver exige une analyse réussie
moins d’une heure auparavant, les mêmes signatures antivirus et un SHA-256
inchangé. Le fichier approuvé est récupérable en téléchargement forcé ; il n’est
pas placé automatiquement dans les assets. Après intégration manuelle au chemin
attendu, utiliser « Marquer intégré » pour supprimer la copie privée, puis lancer `python3 -m tools.build_website` pour actualiser les statuts et la
livraison. Une ressource de qualité basse nécessite aussi de mettre à jour sa
classification dans l’inventaire ; une simple présence ne prouve pas sa qualité.

Avec un tunnel Cloudflare terminé sur un serveur lié à 127.0.0.1, définir
`BOUFBOWL_TRUST_CF=1` pour utiliser CF-Connecting-IP dans les quotas. Ne pas
activer cette option si le proxy local ne garantit pas ce champ. Sans cette
option, les quotas utilisent l’adresse du pair HTTP, ce qui peut regrouper les
visiteurs derrière un proxy. Les adresses ne sont pas stockées en clair par ce
module : elles sont pseudonymisées avec un HMAC et un secret propre au serveur.

Contrôles : `python3 -m unittest tests.test_asset_contributions tests.test_admin`.
Le test ClamAV réel utilise la signature inoffensive EICAR dans un dossier
provisoire ; les autres tests utilisent un scanner simulé pour isoler les règles.

## Atelier des éléments de personnages

`python3 -m tools.build_character_elements` extrait les symboles Crâ M (11.swl)
et F (12.swl), exporte leur première image statique puis produit des WebP
transparents. `tools.build_website` lance aussi cette étape ; les images sont
générées et ignorées par Git. Une empreinte des sources et du script permet de
réutiliser les exports. FFDec, Java et FFmpeg sont nécessaires au premier export.

Le sélecteur contient uniquement les bibliothèques du pantin réellement chargé
par `BoufbowlerSprite.buildEntity` : socle `skins/0.swl`, corps M/F `skins/1.swl`
ou `skins/2.swl`, puis archive spécifique de classe. Les noms sont résolus dans
cet ordre : une pièce spécifique remplace la pièce de même nom du socle.
Les têtes Crâ du socle par défaut ne sont pas présentées comme des pièces
originales des classes manquantes. Les conteneurs `Anim…` assemblés sont exclus.

Les bibliothèques `assets/artworks/*.swf` sont entièrement exclues de cet atelier,
même lorsqu’un nom ressemble à celui d’une partie du corps. Elles contiennent
les illustrations plein écran, leurs variantes et leurs accessoires ; le nom
ou la taille d’une image ne suffit pas à prouver son usage comme pièce de pantin.
Les helpers d’analyse des poses restent utilisés par les contrôles d’archives,
mais ne fournissent plus les entrées de cet atelier.

Le choix « Référence » propose les cinq corps spécifiques retrouvés : Crâ M/F,
Eniripsa F, Enutrof F et Iop M. Pour les autres personnages, l’archive originale absente est listée, sans
supposer ses symboles internes. La liste précédente de 93 emplacements génériques
a été retirée : une intersection entre d’autres classes ne démontre pas ce que
charge le personnage choisi. Le fichier `resources/puppet-slots.json` a été supprimé.

Le rapport `loading` suit la politique `BoufbowlerSprite.buildEntity` du client
actuel : socle 0, corps M/F, puis skin spécifique autorisé ou remplacement Crâ.
Les légendes désactivées utilisent également ce remplacement. Les archives
originales à restaurer sont distinguées des fichiers réellement chargés.
Exemple : Écaflip M charge actuellement `0.swl`, `1.swl`, `11.swl` (Crâ M) ;
`21.swl` est l’original absent, pas une requête de chargement actuelle.

Une archive SWL charge ses symboles ensemble. Leur présence dans cette archive
ne prouve pas une dépendance individuelle ni un usage par toutes les animations.
Sans trace de demandes propre au personnage ou archive originale, aucune liste
de pièces manquantes ne peut être affirmée. Les symboles existants restent
consultables comme inventaire des bibliothèques retrouvées, pas comme besoins
individuels garantis. Le bouton d’envoi conserve le nom exact de l’archive SWL.

## Aperçus originaux et qualité des reconstructions

Le build exporte chaque symbole existant depuis **sa propre archive** en WebP
transparent. La clé de cache contient le chemin de l’archive et le nom du symbole :
`cheveux_d` du Iop ne réutilise donc jamais l’export du Crâ. Les originaux restent
dans leurs archives SWL/SWF ; le WebP est un aperçu dérivé téléchargeable, sans
exécution Flash. Les exports par source sont mis en cache avec empreintes ;
les conversions indépendantes utilisent quatre workers. Les images restent hors Git.

Les grands indicateurs distinguent l’original retrouvé, la reconstruction de bonne
qualité, la reconstruction de qualité basse et la pièce manquante. Une pièce commune originale peut coexister avec une archive spécifique manquante :
les deux états sont présentés séparément. Aucun original n’est qualifié de reconstruction.

Après intégration manuelle d’une pièce au chemin de travail, son niveau peut être
consigné dans `resources/asset-restorations.json` :

```json
{"assets":{"assets/sprites/restoration-elements/21/cheveux.swf":{"quality":"good"}}}
```

`good` et `low` sont les évaluations humaines admises. Sans évaluation, le statut
est « restauré, à vérifier ». Une entrée sans fichier reste manquante. Le build
génère l’aperçu de la reconstruction en isolation, sans ActionScript ; les versions
de qualité basse ou non évaluées peuvent recevoir une meilleure proposition.
L’approbation d’un envoi en quarantaine ne vaut ni intégration ni évaluation de qualité.

Le fichier généré `elements/characters.json` contient les rapports `loading`
(archives effectivement utilisées et remplacement) et `scans` (archive originale
présente/absente et symboles spécifiques retrouvés). Ces informations sont
publiques et téléchargeables depuis l’atelier. Les titres des aperçus restent
alignés et les indicateurs distinguent l’original, la reconstruction et l’absence.
