from handfont_hangul.decomposition import decompose_syllable, layout_regions


def test_unicode_decomposition_examples():
    ga = decompose_syllable("가")
    assert (ga.choseong, ga.jungseong, ga.jongseong) == ("ㄱ", "ㅏ", None)
    assert ga.layout_class == "vertical-open"
    han = decompose_syllable("한")
    assert (han.choseong, han.jungseong, han.jongseong) == ("ㅎ", "ㅏ", "ㄴ")
    assert han.layout_class == "vertical-final"
    gwa = decompose_syllable("과")
    assert gwa.vowel_layout == "compound"
    guk = decompose_syllable("국")
    assert guk.layout_class == "horizontal-final"


def test_layout_regions_match_final_state():
    assert set(layout_regions(decompose_syllable("가"))) == {"choseong", "jungseong"}
    assert set(layout_regions(decompose_syllable("각"))) == {"choseong", "jungseong", "jongseong"}


def test_round_trip_all_modern_syllables():
    from handfont_hangul.decomposition import compose_syllable

    for codepoint in range(0xAC00, 0xD7A4):
        character = chr(codepoint)
        d = decompose_syllable(character)
        assert compose_syllable(d.choseong, d.jungseong, d.jongseong) == character
