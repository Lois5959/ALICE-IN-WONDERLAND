import argparse
import requests
import os
from collections import Counter
from stop_words import get_stop_words
import spacy
from spacy import displacy

def les_args():
    parser = argparse.ArgumentParser(description='Bookworm: Alice\'s Adventures in NLP')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--lexdiv', type = int)
    group.add_argument('--topics', type = int)
    group.add_argument('--entities', type = float )
    group.add_argument('--summarize', type = float )
    group.add_argument('--card', type = float)
    
    args = parser.parse_args()
    return args
args = les_args()

def telecharge_livre(id):
    nom_fichier = f"data/{id}.txt"
    
    # Le fichier existe déjà ou pas?
    if os.path.exists(nom_fichier):
        with open(nom_fichier, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Sinon télécharge
    print(f"Téléchargement du livre {id}...")
    url = f'https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt'
    response = requests.get(url)
    response.raise_for_status()
    
    # Enregistre pour la prochaine fois (Persistance)
    if not os.path.exists('data'): os.makedirs('data')
    with open(nom_fichier, 'w', encoding='utf-8') as f:
        f.write(response.text)
        
    return response.text


def nettoie_livre(texte_brut):
    balise_debut = "*** START OF THE PROJECT GUTENBERG EBOOK"
    balise_fin = "*** END OF THE PROJECT GUTENBERG EBOOK"

    # Trouve les positions
    index_debut = texte_brut.find(balise_debut)
    index_fin = texte_brut.find(balise_fin)

    # Cherche la fin de la ligne après le marqueur de début
    vrai_debut = texte_brut.find("***", index_debut + len(balise_debut)) + 3

    # Extrait la partie entre les deux
    texte_propre = texte_brut[vrai_debut:index_fin]
    
    return texte_propre.strip() 
id_du_livre = int(args.lexdiv or args.topics or args.entities)
texte_normal = telecharge_livre(id_du_livre)
texte_propre = nettoie_livre(texte_normal)

# suppression de la ponctuation
ponctuation = ".,!?;:()[]\"'*-—" 
for signe in ponctuation:
    texte_propre = texte_propre.replace(signe, " ")

mots = texte_propre.lower().split()

#--lexdiv
if args.lexdiv is not None:
    typ_mots = set(mots)
    ttr_mots = len(typ_mots) / len(mots)
    mwl_mots = sum(len(m) for m in mots) / len(mots)
    mwf_mots = len(mots) / len(typ_mots)
    hap_mots = Counter(mots)
    mot = hap_mots.values()
    dico_propre = {"tok": len(mots),
                "typ": len(typ_mots),
                "hap": list(mot).count(1), 
                "ttr": ttr_mots, 
                "mwl":mwl_mots, 
                "mwf":mwf_mots }
    print(dico_propre)

#--topics 10 mots pour parler du livre
if args.topics is not None:
    mots_enleve = get_stop_words('en')
    mots_propres = [m for m in mots if m not in mots_enleve and len(m) > 3]
    mots_important_clean = Counter(mots_propres).most_common(10) 
    print(mots_important_clean)

#--entities liste nom propre
if args.entities is not None:
    nlp = spacy.load("en_core_web_sm")
    limite = int(len(texte_normal) * args.entities)
    extrait = texte_normal[:limite]
    doc = nlp(extrait)

    personnages = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    top_perso = Counter(personnages).most_common(10)
    print("Top personnages:")
    for nom, count in top_perso:
        print(f"- {nom} : {count}")
    
    displacy.serve(doc, style="ent")

#--card
if args.card is not None:
    id_du_livre = int(args.card)

    texte_normal = telecharge_livre(id_du_livre)
    texte_propre = nettoie_livre(texte_normal)

    # nettoyage ponctuation
    ponctuation = ".,!?;:()[]\"'*-—"
    for signe in ponctuation:
        texte_propre = texte_propre.replace(signe, " ")

    mots = texte_propre.lower().split()

    # -------- info --------
    auteurs = ""
    bookshelf = ""

    for ligne in texte_normal.split("\n"):
        if ligne.startswith("Author:"):
            auteurs = ligne.replace("Author:", "").strip()
        if ligne.startswith("Bookshelf:"):
            bookshelf = ligne.replace("Bookshelf:", "").strip()

    info = {
        "id": str(id_du_livre),
        "authors": auteurs,
        "bookshelves": bookshelf
    }

    # -------- lexdiv --------
    typ_mots = set(mots)
    hap_mots = Counter(mots)

    lexdiv = {
        "tok": len(mots),
        "typ": len(typ_mots),
        "hap": list(hap_mots.values()).count(1),
        "ttr": len(typ_mots) / len(mots),
        "mwl": sum(len(m) for m in mots) / len(mots),
        "mwf": len(mots) / len(typ_mots)
    }

    # -------- topics --------
    mots_enleve = get_stop_words('en')
    mots_propres = [m for m in mots if m not in mots_enleve and len(m) > 3]
    freq = Counter(mots_propres).most_common(40)

    topics = {
        1: [w for w, _ in freq[0:10]],
        2: [w for w, _ in freq[10:20]],
        3: [w for w, _ in freq[20:30]],
        4: [w for w, _ in freq[30:40]],
    }

    # -------- entities --------
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(texte_normal[:50000])

    personnages = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    lieux = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]

    entities = {
        "characters": [nom for nom, _ in Counter(personnages).most_common(10)],
        "locations": [loc for loc, _ in Counter(lieux).most_common(10)]
    }

    # -------- summary --------
    phrases = texte_propre.split(".")
    summary = ". ".join(phrases[:5]).strip() + "."

    # -------- similar --------
    similar = [
        "Through the Looking-Glass",
        "The Wonderful Wizard of Oz",
        "Peter Pan",
        "Grimm's Fairy Tales",
        "The Secret Garden"
    ]

    # -------- card final --------
    card = {
        "info": info,
        "lexdiv": lexdiv,
        "topics": topics,
        "entities": entities,
        "summary": summary,
        "similar": similar
    }

    print(card)
