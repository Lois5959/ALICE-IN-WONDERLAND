import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bookworm  # noqa: E402

TEXTE_GUTENBERG = (
    "Title: Test\nAuthor: Lewis Carroll\n\n"
    "*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
    "Alice was beginning to get very tired.\n"
    "*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
    "Licence Gutenberg..."
)


def test_nettoie_livre_garde_seulement_le_texte():
    assert bookworm.nettoie_livre(TEXTE_GUTENBERG) == "Alice was beginning to get very tired."


def test_nettoie_livre_sans_marqueurs():
    assert bookworm.nettoie_livre("  juste du texte  ") == "juste du texte"


def test_decoupe_mots_retire_la_ponctuation():
    assert bookworm.decoupe_mots("“Oh dear!” said Alice—again.") == ["oh", "dear", "said", "alice", "again"]


def test_lexdiv():
    mesures = bookworm.lexdiv(["the", "cat", "the", "dog"])
    assert mesures["tok"] == 4
    assert mesures["typ"] == 3
    assert mesures["hap"] == 2          # cat et dog n'apparaissent qu'une fois
    assert mesures["ttr"] == pytest.approx(0.75)
    assert mesures["mwf"] == pytest.approx(4 / 3)


def test_lexdiv_texte_vide():
    assert bookworm.lexdiv([])["tok"] == 0


def test_topics_ignore_les_mots_vides():
    mots = ["alice", "alice", "rabbit", "the", "and", "the", "queen"]
    assert bookworm.topics(mots)[1] == ["alice", "rabbit", "queen"]


def test_topics_par_groupes_de_10():
    mots = [f"mot{i:02d}" for i in range(40) for _ in range(40 - i)]
    groupes = bookworm.topics(mots, nb_groupes=4)
    assert list(groupes) == [1, 2, 3, 4]
    assert all(len(g) == 10 for g in groupes.values())
    assert groupes[1][0] == "mot00"


def test_info_lit_l_auteur():
    fiche = bookworm.info(11, TEXTE_GUTENBERG)
    assert fiche["authors"] == "Lewis Carroll"
    assert fiche["bookshelves"] == "Children"


def test_id_inconnu_refuse_sans_telecharger(monkeypatch, capsys):
    def interdit(_):
        raise AssertionError("ne doit pas télécharger")
    monkeypatch.setattr(bookworm, "telecharge_livre", interdit)
    assert bookworm.main(["--lexdiv", "99"]) == 1
    assert "ne fait pas partie" in capsys.readouterr().err


def test_lexdiv_sur_un_livre_du_cache(capsys):
    assert bookworm.main(["--lexdiv", "11"]) == 0
    assert "'tok'" in capsys.readouterr().out
