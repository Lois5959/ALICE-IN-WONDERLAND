"""Bookworm : Alice's Adventures in NLP.

Analyse de livres du Projet Gutenberg en ligne de commande :
diversité lexicale, thèmes, personnages, résumé, livres similaires et fiche complète.

Exemples :
    python bookworm.py --lexdiv 11
    python bookworm.py --card 11
"""
import argparse
import heapq
import json
import os
import sys
from collections import Counter

import requests
from stop_words import get_stop_words

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# id Gutenberg -> (titre, rayon)
BIBLIOTHEQUE = {
    11: ("Alice's Adventures in Wonderland", "Children"),
    12: ("Through the Looking-Glass", "Children"),
    16: ("Peter Pan", "Children"),
    55: ("The Wonderful Wizard of Oz", "Children"),
    113: ("The Secret Garden", "Children"),
    120: ("Treasure Island", "Children"),
    236: ("The Jungle Book", "Children"),
    108: ("The Return of Sherlock Holmes", "Crime"),
    834: ("The Memoirs of Sherlock Holmes", "Crime"),
    863: ("The Mysterious Affair at Styles", "Crime"),
    1661: ("The Adventures of Sherlock Holmes", "Crime"),
    61262: ("Poirot Investigates", "Crime"),
    69087: ("The Murder of Roger Ackroyd", "Crime"),
    70114: ("The Big Four", "Crime"),
    35: ("The Time Machine", "Science Fiction"),
    36: ("The War of the Worlds", "Science Fiction"),
    84: ("Frankenstein; Or, The Modern Prometheus", "Science Fiction"),
    159: ("The Island of Doctor Moreau", "Science Fiction"),
    164: ("Twenty Thousand Leagues under the Sea", "Science Fiction"),
    345: ("Dracula", "Gothic"),
}

PONCTUATION = ".,!?;:()[]\"'*-—_“”‘’"
TAILLE_EXTRAIT = 50000  # caractères analysés par spaCy (résumé, entités)

_nlp = None


# ---------- chargement ----------

def telecharge_livre(id_livre):
    """Retourne le texte brut du livre, depuis le cache data/ ou Gutenberg."""
    nom_fichier = os.path.join(DATA_DIR, f"{id_livre}.txt")

    if os.path.exists(nom_fichier):
        with open(nom_fichier, "r", encoding="utf-8") as f:
            return f.read()

    print(f"Téléchargement du livre {id_livre}...", file=sys.stderr)
    url = f"https://www.gutenberg.org/cache/epub/{id_livre}/pg{id_livre}.txt"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(nom_fichier, "w", encoding="utf-8") as f:
        f.write(response.text)

    return response.text


def nettoie_livre(texte_brut):
    """Garde seulement le texte du livre, entre les marqueurs START et END de Gutenberg."""
    balise_debut = "*** START OF THE PROJECT GUTENBERG EBOOK"
    balise_fin = "*** END OF THE PROJECT GUTENBERG EBOOK"

    index_debut = texte_brut.find(balise_debut)
    index_fin = texte_brut.find(balise_fin)

    if index_debut == -1:
        debut = 0
    else:
        # le marqueur de début se termine par "***" sur la même ligne
        debut = texte_brut.find("***", index_debut + len(balise_debut)) + 3
    fin = index_fin if index_fin != -1 else len(texte_brut)

    return texte_brut[debut:fin].strip()


def decoupe_mots(texte):
    """Retire la ponctuation et renvoie la liste des mots en minuscules."""
    for signe in PONCTUATION:
        texte = texte.replace(signe, " ")
    return texte.lower().split()


def charge_nlp():
    """Charge le modèle spaCy une seule fois."""
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            sys.exit("Modèle spaCy manquant : python -m spacy download en_core_web_sm")
    return _nlp


# ---------- analyses ----------

def lexdiv(mots):
    """Mesures de diversité lexicale."""
    if not mots:
        return {"tok": 0, "typ": 0, "hap": 0, "ttr": 0.0, "mwl": 0.0, "mwf": 0.0}
    types = set(mots)
    frequences = Counter(mots)
    return {
        "tok": len(mots),                                   # nombre de mots
        "typ": len(types),                                  # mots différents
        "hap": list(frequences.values()).count(1),          # mots vus une seule fois
        "ttr": len(types) / len(mots),                      # type/token ratio
        "mwl": sum(len(m) for m in mots) / len(mots),       # longueur moyenne d'un mot
        "mwf": len(mots) / len(types),                      # fréquence moyenne d'un mot
    }


def mots_significatifs(mots):
    """Mots sans les mots vides (the, and...) et de plus de 3 lettres."""
    mots_vides = set(get_stop_words("en"))
    return [m for m in mots if m not in mots_vides and len(m) > 3]


def topics(mots, nb_groupes=1):
    """Mots les plus fréquents, en groupes de 10."""
    frequents = [mot for mot, _ in Counter(mots_significatifs(mots)).most_common(10 * nb_groupes)]
    return {i + 1: frequents[i * 10:(i + 1) * 10] for i in range(nb_groupes)}


def entites(texte):
    """Personnages et lieux les plus cités (reconnaissance d'entités nommées)."""
    doc = charge_nlp()(texte[:TAILLE_EXTRAIT])
    personnages = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
    lieux = [ent.text.strip() for ent in doc.ents if ent.label_ in ("GPE", "LOC")]
    return {
        "characters": [nom for nom, _ in Counter(personnages).most_common(10)],
        "locations": [lieu for lieu, _ in Counter(lieux).most_common(10)],
    }, doc


def resume(texte, nb_phrases=3):
    """Résumé extractif : garde les phrases qui contiennent les mots les plus fréquents."""
    doc = charge_nlp()(texte[:TAILLE_EXTRAIT])

    mots_utiles = [token.text.lower() for token in doc
                   if not token.is_stop and not token.is_punct and len(token.text.strip()) > 3]
    frequence = Counter(mots_utiles)

    score_phrases = {}
    for phrase in doc.sents:
        # on ignore les phrases trop courtes (dialogues) ou trop longues (paragraphes entiers)
        if not 8 <= len(phrase) <= 40:
            continue
        score_phrases[phrase] = sum(frequence.get(token.text.lower(), 0) for token in phrase)

    meilleures = heapq.nlargest(nb_phrases, score_phrases, key=score_phrases.get)
    meilleures.sort(key=lambda phrase: phrase.start)  # remet dans l'ordre du livre
    return " ".join(" ".join(p.text.split()) for p in meilleures)


def similaires(id_cible, nb=5):
    """Livres les plus proches (TF-IDF + similarité cosinus sur toute la bibliothèque)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    ids = list(BIBLIOTHEQUE)
    corpus = [nettoie_livre(telecharge_livre(book_id)) for book_id in ids]

    matrice = TfidfVectorizer(stop_words="english").fit_transform(corpus)
    scores = cosine_similarity(matrice[ids.index(id_cible)], matrice)[0]

    classement = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
    return [BIBLIOTHEQUE[book_id][0] for book_id, _ in classement if book_id != id_cible][:nb]


def info(id_livre, texte_brut):
    """Métadonnées lues dans l'en-tête Gutenberg."""
    auteurs = ""
    for ligne in texte_brut.split("\n"):
        if ligne.startswith("Author:"):
            auteurs = ligne.replace("Author:", "").strip()
            break
    titre, rayon = BIBLIOTHEQUE[id_livre]
    return {
        "id": str(id_livre),
        "title": titre,
        "authors": auteurs,
        "bookshelves": rayon,
        "cover": f"https://www.gutenberg.org/cache/epub/{id_livre}/pg{id_livre}.cover.medium.jpg",
    }


def fiche(id_livre, texte_brut, texte):
    """Fiche complète du livre (toutes les analyses)."""
    mots = decoupe_mots(texte)
    entities, _ = entites(texte)
    return {
        "info": info(id_livre, texte_brut),
        "lexdiv": lexdiv(mots),
        "topics": topics(mots, nb_groupes=4),
        "entities": entities,
        "summary": resume(texte),
        "similar": similaires(id_livre),
    }


# ---------- ligne de commande ----------

def les_args(argv=None):
    parser = argparse.ArgumentParser(description="Bookworm: Alice's Adventures in NLP")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lexdiv", type=int, metavar="ID", help="diversité lexicale")
    group.add_argument("--topics", type=int, metavar="ID", help="10 mots qui résument le livre")
    group.add_argument("--entities", type=int, metavar="ID", help="personnages principaux")
    group.add_argument("--summarize", type=int, metavar="ID", help="résumé en 3 phrases")
    group.add_argument("--similar", type=int, metavar="ID", help="5 livres les plus proches")
    group.add_argument("--card", type=int, metavar="ID", help="fiche complète en JSON")
    group.add_argument("--list", action="store_true", help="liste des livres disponibles")
    parser.add_argument("--serve", action="store_true",
                        help="avec --entities : affiche les entités dans le navigateur (displaCy)")
    return parser.parse_args(argv)


def main(argv=None):
    args = les_args(argv)

    if args.list:
        for book_id, (titre, rayon) in BIBLIOTHEQUE.items():
            print(f"{book_id:>6}  {titre}  ({rayon})")
        return 0

    id_livre = next(v for v in (args.lexdiv, args.topics, args.entities,
                                args.summarize, args.similar, args.card) if v is not None)

    # on vérifie l'id AVANT de télécharger quoi que ce soit
    if id_livre not in BIBLIOTHEQUE:
        print(f"L'id {id_livre} ne fait pas partie de la bibliothèque (voir --list)", file=sys.stderr)
        return 1

    try:
        texte_brut = telecharge_livre(id_livre)
    except requests.RequestException as e:
        print(f"Impossible de télécharger le livre {id_livre} : {e}", file=sys.stderr)
        return 1
    texte = nettoie_livre(texte_brut)

    if args.lexdiv is not None:
        print(lexdiv(decoupe_mots(texte)))

    elif args.topics is not None:
        print(topics(decoupe_mots(texte))[1])

    elif args.entities is not None:
        entities, doc = entites(texte)
        print("Top personnages :")
        for nom in entities["characters"]:
            print(f"- {nom}")
        if args.serve:
            from spacy import displacy
            displacy.serve(doc, style="ent")

    elif args.summarize is not None:
        print(f"Summary of book {id_livre}:\n{resume(texte)}")

    elif args.similar is not None:
        for titre in similaires(id_livre):
            print(f"- {titre}")

    elif args.card is not None:
        print(json.dumps(fiche(id_livre, texte_brut, texte), indent=4, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
