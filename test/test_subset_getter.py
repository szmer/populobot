from popbot_src.section import Section
from popbot_src.subset_getter import weight_index

class TestSubsetGetter():
    def test_weight_index(self):
        config1 = { 'book_title': 'book', 'palatinate': 'A', 'default_convent_author': 'someone',
                    'convent_location': 'nowhere' }
        config2 = { 'book_title': 'book', 'palatinate': 'B', 'default_convent_author': 'someone',
                    'convent_location': 'nowhere' }
        config3 = { 'book_title': 'book', 'palatinate': 'C', 'default_convent_author': 'someone',
                    'convent_location': 'nowhere' }
        test_index = dict([('palatinate__A', [Section.new(config1, 'document', [(1, 'ttl'), (1, 'aaa')]),
                                              Section.new(config1, 'document', [(1, 'ttl'), (1, 'bbb')]),
                                              Section.new(config1, 'document', [(1, 'ttl'), (1, 'ccc')])]),
                           ('palatinate__B', [Section.new(config2, 'document', [(1, 'ttl'), (1, 'ddd')]),
                                              Section.new(config2, 'document', [(1, 'ttl'), (1, 'eee')])]),
                           ('palatinate__C', [Section.new(config3, 'document', [(1, 'ttl'), (1, 'ff')]),
                                              Section.new(config3, 'document', [(1, 'ttl'), (1, 'hh')]),
                                              Section.new(config3, 'document', [(1, 'ttl'), (1, 'ii')])])])
        test_weightings = {'A': 3, 'B': 3, 'C': 3, 'D': 4}
        weighted_index = weight_index(test_index, ['palatinate', 'book_title'],
                                      'palatinate', test_weightings)
        # Weight_index puts correct indices.
        indices = [ind for (ind, secs) in weighted_index.items()]
        assert 'palatinate__A' in indices
        assert 'palatinate__B' in indices
        assert 'palatinate__C' in indices
        assert 'book_title__book' in indices
        assert not 'palatinate__D' in indices # values not present should be skipped
        # Palatinate indices have correct scaled sizes.
        assert 2 == len(weighted_index['palatinate__A'])
        assert 2 == len(weighted_index['palatinate__B'])
        assert 3 == len(weighted_index['palatinate__C']) # more because of the shorter texts
        assert 7 == len(weighted_index['book_title__book'])
