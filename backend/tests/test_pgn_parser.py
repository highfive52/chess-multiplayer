from backend.services.pgn_import import parse_pgn


def test_parse_simple_pgn():
    pgn = """[Event "Test"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""
    games = parse_pgn(pgn)
    assert len(games) == 1
    g = games[0]
    assert g.metadata.get("White") == "Alice"
    assert len(g.moves) == 6
    assert g.moves[0].san == "e4"
    assert g.moves[-1].san in ("a6",)
