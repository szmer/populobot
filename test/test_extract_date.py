from popbot_src.load_helpers import extract_dates

def test_extract_dates():
    assert extract_dates("4. U niwe-rsal zjazdu do starostów o dawanie pomocy posłom, wysłanym do k-ro'lewnej Anny do Płocka, z Osieka- 4 października 1572 -r. eis huiuscemodi litteris. Uw. Po akcie pomieszczone ~w rękopisie. mz k. 72—72") == [(4, 10, 1572)]
    assert extract_dates('9 V 1755') == [(9, 5, 1755)]
    assert extract_dates('64. Wisnia, 24. maja 1683. Laudum sejmiku wiszeńskiego (fragment). ') == [(24, 5, 1683)]
    assert extract_dates('Działo się wRadziejowie die 22 Junii,anno 1705.') == [(22, 6, 1705)]
    assert extract_dates('Februarius, 16. 1703') == [(16, 2, 1703)]
    # we use only the 1500-1799 dates
    assert extract_dates('Februarius, 16. 1803') == []
    assert extract_dates('Februarius, 30. 1703') == []
    assert extract_dates('1650 Februarius, 3. 173') == [(3, 2, 1650)]
    assert extract_dates('(Junius, 28), anno Domini 1706.') == [(28, 6, 1706)]
