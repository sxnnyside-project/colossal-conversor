# Colossal Conversor — Guide de l'Utilisateur

<p align="center">
  <em>Tout ce qu'il faut pour installer, utiliser et dépanner Colossal Conversor au quotidien.</em>
</p>

<p align="center">
  <sub>Langues : <a href="../en/README.md">English</a> · <a href="../es/README.md">Español</a> · <a href="../fr/README.md">Français</a> · <a href="../ja/README.md">日本語</a> · <a href="../pt/README.md">Português</a> · <a href="../zh/README.md">中文</a></sub>
</p>

---

## 1. Qu'est-ce que Colossal Conversor ?

Colossal Conversor est une application de bureau hors ligne pour convertir
des fichiers audio, vidéo, image, document, tableur et présentation. Tout
s'exécute localement grâce à un noyau d'exécution natif en C++20 — pas
d'envoi vers le cloud, pas de compte, aucune dépendance réseau pour la
conversion elle-même. Consultez le [README](../../../README.md) principal
pour la présentation technique complète.

Ce guide couvre l'utilisation quotidienne réelle de l'application :
installation, première conversion, traitement par lots et pipelines, et
comment se rétablir quand quelque chose ne va pas.

## 2. Plateformes Prises en Charge

Colossal Conversor cible **macOS, Linux et Windows**. Le superviseur de
processus natif dispose d'un backend dédié par plateforme, de sorte que la
création de processus, la capture de sortie, l'annulation et le nettoyage
se comportent de la même façon partout.

| Plateforme | État |
|---|---|
| macOS | Vérifiée — compilée, testée et utilisée pour le développement quotidien |
| Linux | Implémentée (partage le backend macOS) ; pas encore vérifiée sur un runner Linux |
| Windows | Implémentée selon les API de processus Windows ; pas encore vérifiée sur un runner Windows |

« Implémentée mais pas encore vérifiée » signifie que le code existe et
respecte les bons contrats de plateforme, mais que personne n'a encore
confirmé qu'une conversion réelle aboutit sur cette plateforme. Ce statut
sera mis à jour au fur et à mesure des vérifications — consultez la section
Plateformes du README principal pour le statut actuel, et
[CONTRIBUTING.md](../../../CONTRIBUTING.md) si vous souhaitez aider à
vérifier Linux ou Windows.

## 3. Installation

Installer Colossal Conversor lui-même est distinct de l'installation des
outils externes utilisés pour certaines conversions (voir la section
Dépendances Externes ci-dessous).

### macOS / Linux

```bash
git clone https://github.com/sxnnyside-project/colossal-conversor.git
cd colossal-conversor
just install
just dev
```

### Windows

```powershell
git clone https://github.com/sxnnyside-project/colossal-conversor.git
cd colossal-conversor
just install
just dev
```

`just install` synchronise les dépendances Python et compile l'extension
native. `just dev` lance l'application. Si vous n'avez pas `just`,
consultez ses [instructions d'installation](https://github.com/casey/just#installation)
— ou exécutez l'équivalent `uv sync --all-groups` suivi de la compilation
native CMake décrite dans le README principal.

## 4. Dépendances Externes

Certaines catégories de conversion appellent un outil externe ; d'autres
s'exécutent entièrement en interne et ne nécessitent rien de plus.

| Outil | Nécessaire pour |
|---|---|
| FFmpeg | Conversions audio et vidéo |
| LibreOffice | Conversions de documents, tableurs et présentations |
| Poppler (`pdftoppm`) | Rendu de pages de document en image |
| Pandoc | Conversions markdown ↔ document |
| ImageMagick | Conversions d'image autres que BMP/PPM/TGA (natives, sans outil requis) |

Pour vérifier ce qui est déjà disponible :

```bash
just verify-tools
```

Pour installer ce qui manque :

- **macOS** : `bash tools/macos_install_deps.sh` (Homebrew)
- **Linux** : `bash tools/linux_install_deps.sh` (apt, dnf ou pacman — détecté automatiquement)
- **Windows** : exécutez `tools/windows_install_deps.ps1` dans PowerShell (winget, ou Chocolatey si déjà installé)

Installer ces outils **ne garantit pas** à lui seul que toute conversion
fonctionnera — cela rend le moteur correspondant disponible. L'application
détecte chaque outil au moment de l'exécution et ne propose que les
conversions qu'elle peut réellement effectuer.

## 5. Première Conversion

1. Lancez l'application (`just dev`).
2. Cliquez sur **Select File(s)** ou glissez un fichier dans la zone de dépôt.
3. Colossal Conversor détecte le format d'entrée et n'affiche que les
   formats de destination qu'il peut réellement produire, regroupés par
   catégorie.
4. Cliquez sur un format de destination.
5. Cliquez sur **Save As...** pour choisir (ou confirmer) la destination,
   si vous voulez autre chose que la valeur par défaut.
6. Cliquez sur **Convert** (ou appuyez sur <kbd>Enter</kbd>).

À la fin, une boîte de dialogue indique combien de fichiers ont été
produits, avec des boutons pour ouvrir le résultat ou le révéler dans votre
gestionnaire de fichiers.

## 6. Fichiers Multiples

Cliquez sur **Select File(s)** et choisissez plusieurs fichiers, ou
glissez-en plusieurs à la fois. Colossal Conversor n'affiche que les
formats de sortie communs à toutes les entrées sélectionnées. Choisissez un
**dossier** de destination (pas un fichier unique) via **Save As...**, puis
**Convert** — chaque entrée produit sa propre sortie dans ce dossier.

## 7. Conversions à Sorties Multiples

Certaines conversions produisent plusieurs fichiers à partir d'une seule
entrée — par exemple, le rendu de chaque page d'un PDF en image distincte.
Cela est détecté automatiquement selon la paire de formats choisie ; la
destination choisie devient un dossier contenant toutes les pages
produites, et la boîte de dialogue finale indique le nombre réel de
fichiers générés.

## 8. Pipelines

Certaines conversions ne peuvent pas se faire en une seule étape et sont
automatiquement découpées en étapes internes — par exemple, une
présentation convertie en image passe d'abord par un PDF intermédiaire.
Aucune configuration n'est nécessaire : choisissez votre entrée et le
format de destination comme d'habitude, et la barre de progression indique
quelle étape est en cours. Les fichiers intermédiaires sont nettoyés
automatiquement une fois le pipeline terminé (ou en cas d'échec ou
d'annulation).

## 9. Choisir un Format de Sortie

La grille de formats n'affiche que les destinations que Colossal Conversor
peut réellement produire à partir de votre entrée actuelle — elle
n'annonce jamais une conversion qu'elle ne peut pas exécuter. Lorsque vous
sélectionnez un format, une note de fidélité apparaît (par exemple « high »,
« medium », « layout ») décrivant à quel point la sortie préserve
l'original — utile lors de la conversion entre formats aux capacités
différentes (par exemple, un document stylé vers du texte brut).

## 10. Sélection de la Destination

**Save As...** permet de choisir où va la sortie. Pour une conversion à
sortie unique, choisissez un chemin de fichier ; pour un lot ou une
conversion à sorties multiples, choisissez un dossier. Si vous ne
choisissez pas explicitement, l'application propose une destination
raisonnable à côté du fichier d'entrée.

## 11. Annulation

Cliquez sur **Cancel** pendant qu'une conversion est en cours pour
l'arrêter. Cela met réellement fin au processus sous-jacent (pas seulement
à l'état de l'interface) — aucune sortie partielle n'est signalée comme un
résultat réussi, et la barre d'état affiche « Conversion cancelled »,
distinct à la fois d'un succès et d'un échec. Vous pouvez démarrer une
nouvelle conversion immédiatement après.

## 12. Erreurs et Récupération

Si une conversion échoue, une boîte de dialogue explique ce qui s'est passé
en langage clair, avec un bouton **Show Details...** pour la sortie
technique sous-jacente (affichée uniquement si vous le demandez).
L'application ne plante pas et ne se bloque pas suite à une conversion
échouée — fermez la boîte de dialogue et réessayez, en ajustant l'entrée,
le format de destination ou la destination selon les besoins.

## 13. Dépendances Manquantes

Si une conversion nécessite un outil qui n'est pas installé, le message
d'erreur le précise explicitement et nomme l'outil — il ne sera pas
confondu avec un échec générique. Exécutez `just verify-tools` pour voir
l'état complet, et consultez la section Dépendances Externes ci-dessus pour
installer ce qui manque.

## 14. Formats Pris en Charge

La grille de formats dans l'application est la liste faisant autorité, en
temps réel — elle est générée à partir du même catalogue que celui utilisé
par le moteur de conversion, donc elle ne peut jamais annoncer quelque
chose que la version actuelle ne peut pas réellement faire. En termes
généraux, Colossal Conversor prend en charge :

- **Audio** : formats courants tels que MP3, WAV, FLAC, AAC, OGG, et d'autres.
- **Vidéo** : formats courants tels que MP4, MKV, MOV, AVI, WebM, et d'autres.
- **Image** : formats courants tels que PNG, JPEG, WebP, BMP, TIFF, GIF, et d'autres.
- **Document** : DOC/DOCX, ODT, RTF, TXT, PDF, Markdown, HTML, EPUB.
- **Tableur** : XLS/XLSX, ODS, CSV, TSV.
- **Présentation** : PPTX/PPT, ODP.

Sélectionnez un fichier d'entrée dans l'application pour voir la liste
exacte et actuelle des destinations pour ce fichier en particulier.

## 15. Dépannage

**Une conversion que j'attendais n'est pas proposée.** La liste des formats
de destination est générée à partir du format détecté de votre entrée
spécifique — vérifiez que l'entrée a été correctement détectée (affiché à
côté du nom du fichier) et que la conversion souhaitée est bien prise en
charge pour cette paire de formats.

**Erreur « dépendance manquante ».** Exécutez `just verify-tools`, puis
installez l'outil nommé (voir Dépendances Externes / Dépendances Manquantes
ci-dessus).

**La conversion échoue immédiatement.** Consultez **Show Details...** dans
la boîte de dialogue d'erreur. Causes courantes : un fichier d'entrée
corrompu ou illisible, ou un format que l'entrée détectée ne correspond
pas réellement (par exemple, un fichier renommé avec la mauvaise
extension).

**Cancel ne semble rien faire visuellement.** Pour les conversions très
courtes, l'opération peut se terminer avant que Cancel ne prenne effet —
c'est normal, pas un bug ; le résultat sera un succès ou un échec normal,
pas une interface bloquée.

**Le chemin de destination n'est pas valide.** Assurez-vous que le dossier
existe et que vous avez les droits d'écriture ; pour une sortie à fichier
unique, assurez-vous que le dossier parent existe.

**Toujours bloqué ?** Ouvrez un ticket — voir [SUPPORT.md](../../../SUPPORT.md).

---

<p align="center">
  <sub>Fait partie de la documentation de <a href="../../../README.md">Colossal Conversor</a> — A Sxnnyside Project Release</sub>
</p>
