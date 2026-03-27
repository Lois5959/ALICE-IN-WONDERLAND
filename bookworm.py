import argparse
import requests
import os
import json
import heapq
from collections import Counter
from stop_words import get_stop_words
import spacy
from spacy import displacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

bibliotheque = {
    11: "Alice's Adventures in Wonderland",
    12: "Through the Looking-Glass",
    16: "Peter Pan",
    55: "The Wonderful Wizard of Oz Children",
    113: "The Secret Garden Children", 
    120: "Treasure Island Children" ,
    236: "The Jungle Book Children",
    108: "The Return of Sherlock Holmes Crime",
    834: "The Memoirs of Sherlock Holmes Crime",
    863: "The Mysterious Affair at Styles Crime",
    1661: "The Adventures of Sherlock Holmes Crime", 
    61262: "Poirot Investigates Crime",
    69087: "The murder of Roger Ackroyd Crime", 
    70114: "The Big Four Crime", 
    35: "The Time Machine",
    36: "The War of the Worlds",
    84:"Frankenstein; Or, The Modern Prometheus", 
    159: "The island of Doctor Moreau", 
    164:"Twenty Thousand Leagues under the Sea",
    345: "Dracula"
}
    



def les_args():
    parser = argparse.ArgumentParser(description='Bookworm: Alice\'s Adventures in NLP')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--lexdiv', type = int)
    group.add_argument('--topics', type = int)
    group.add_argument('--entities', type = float )
    group.add_argument('--summarize', type = float )
    group.add_argument('--card', type=int) 
    group.add_argument('--similar', type=int) 
    
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

valeur_id = int(args.lexdiv or args.topics or args.entities or args.card or args.summarize or args.similar)
id_du_livre = int(valeur_id) if valeur_id is not None else None
texte_normal = telecharge_livre(id_du_livre)
texte_propre = nettoie_livre(texte_normal)

if id_du_livre not in bibliotheque:
    print(f"L'id {id_du_livre} ne fait pas partie de la bibliothèque")
    exit(1)




def generer_resume(texte_propre, id_du_livre):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(texte_propre[:50000])
    
    mots_utiles = [token.text.lower() for token in doc 
                   if not token.is_stop and not token.is_punct and len(token.text.strip()) > 3]
    frequence_mots = Counter(mots_utiles)
    
    score_phrases = {}
    for sent in doc.sents:
        for word in sent:
            word_clean = word.text.lower()
            if word_clean in frequence_mots:
                score_phrases[sent] = score_phrases.get(sent, 0) + frequence_mots[word_clean]
    
    meilleures_phrases = heapq.nlargest(3, score_phrases, key=score_phrases.get)
    return " ".join([p.text.replace('\n', ' ').strip() for p in meilleures_phrases])



def obtenir_similarites(id_cible, bibliotheque):
    id_a_traiter = list(bibliotheque.keys())
    corpus_texte = []
    
    for book_id in id_a_traiter:
        raw = telecharge_livre(book_id) 
        clean = nettoie_livre(raw)     
        corpus_texte.append(clean)

    tfidf = TfidfVectorizer(stop_words='english')
    resultat = tfidf.fit_transform(corpus_texte)
    
    idx = id_a_traiter.index(id_cible)
    scores = cosine_similarity(resultat[idx], resultat)[0]
    
    # Top 5
    recos = []
    for i in range(len(id_a_traiter)):
        recos.append((bibliotheque[id_a_traiter[i]], scores[i]))
    
    recos_triees = sorted(recos, key=lambda x: x[1], reverse=True)
    return [livre[0] for livre in recos_triees[1:6]]



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

    with open("data/clean_temp.txt", "w") as f:
        f.write(" ".join(mots_propres))



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



# --summarize
if args.summarize is not None:
    resume = generer_resume(texte_propre, id_du_livre)
    print(f"\nSummary of book {id_du_livre}:\n{resume}")



#--similar
if args.similar is not None:
    id_user = int(args.similar)
    if id_user in bibliotheque:
        print(obtenir_similarites(id_user, bibliotheque))
    else:
        print("id inconnu")



#--card
if args.card is not None:
    id_du_livre = int(args.card)

    texte_normal = telecharge_livre(id_du_livre)
    texte_propre = nettoie_livre(texte_normal)

    # nettoyage ponctuation
    ponctuation = ".,!?;:()[]\"'*-—“"
    for signe in ponctuation:
        texte_propre = texte_propre.replace(signe, " ")

    mots = texte_propre.lower().split()

    # -------- info --------
    auteurs = ""
    bookshelf = ""
    cover_url = f"https://www.gutenberg.org/cache/epub/{id_du_livre}/pg{id_du_livre}.cover.medium.jpg"

    for ligne in texte_normal.split("\n"):
        if ligne.startswith("Author:"):
            auteurs = ligne.replace("Author:", "").strip()
        if ligne.startswith("Bookshelf:"):
            bookshelf = ligne.replace("Bookshelf:", "").strip()

    info = {
        "id": str(id_du_livre),
        "authors": auteurs,
        "bookshelves": bookshelf,
        "cover": cover_url
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

# 40 mots plus fréquents
    freq = Counter(mots_propres).most_common(40)

#coupe en groupe de 10
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
    
    # -------- card final --------
    card = {
        "info": info,
        "lexdiv": lexdiv,
        "topics": topics,
        "entities": entities,
        "summary": generer_resume(texte_propre, id_du_livre), 
        "similar": obtenir_similarites(id_du_livre, bibliotheque)
        
    }
    print(f"IMAGE DU LIVRE : {info['cover']}")
    print("="*50)
    
    card_lisible = json.dumps(card, indent=4, ensure_ascii=False)
    print(card_lisible)