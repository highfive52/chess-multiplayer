from backend.services.pgn_import import parse_pgn


def test_detect_comments_and_nags(tmp_path):
    text = '[Event "Test"]\n\n1. e4 {a comment} e5 2. Nf3!? Nc6\n'
    parsed_games = parse_pgn(text)
    assert len(parsed_games) == 1
    parsed = parsed_games[0]
    assert "COMMENTS_IGNORED" in parsed.warnings
    assert "NAGS_IGNORED" in parsed.warnings


def test_detect_variations(tmp_path):
    text = '[Event "Var"]\n\n1. e4 (1... c5 2. Nf3) e5 2. Nf3 Nc6\n'
    parsed_games = parse_pgn(text)
    assert len(parsed_games) == 1
    parsed = parsed_games[0]
    assert "VARIATIONS_IGNORED" in parsed.warnings


def test_unknown_tags_reported():
    text = '[Event "X"]\n[CustomTag "value"]\n\n1. e4 e5\n'
    parsed_games = parse_pgn(text)
    parsed = parsed_games[0]
    assert "UNKNOWN_TAGS_IGNORED" in parsed.warnings
