class NoneTokenError(Exception):
    pass

class ParsedToken():
    """
    The class for saving parsed tokens obtained by morpho.py.
    """
    def __init__(self, form, lemma, interp, position=False,
            proper_name=False, unknown_form=False, latin=False, corrected=False,
            pause='', corresp_index=False, chosen=True, sentence_starting=False):
        self.form = form
        self.lemma = lemma
        if not isinstance(interp, list):
            interp = interp.split(':')
        self.interp = interp
        self.proper_name = proper_name
        self.unknown_form = unknown_form
        self.latin = latin
        self.corrected = corrected
        self.position = position
        # Pause is the string that separates this token from the previous one.
        self.pause = pause
        # The index in the original paragraph where the token starts.
        self.corresp_index = corresp_index
        self.chosen = chosen # whether the token was chosen during disambiguation
        self.forward_paths = [] # all possible tokens after this one in the sentence DAG
        self.sentence_starting = sentence_starting

    @classmethod
    def from_str(cls, token_str):
        if token_str.strip() == '':
            raise NoneTokenError
        semantic_fields = token_str.split('_')
        morpho_fields = '_'.join([f for f in semantic_fields if not f in ['PN', '??', '!!', 'LA']]).split(':')
        self = cls(morpho_fields[0], morpho_fields[1],  ':'.join(morpho_fields[2:]))
        self.proper_name = 'PN' in semantic_fields
        self.unknown_form = '??' in semantic_fields
        self.latin = 'LA' in semantic_fields
        self.corrected = '!!' in semantic_fields
        self.form = morpho_fields[0]
        self.lemma = morpho_fields[1]
        self.interp = morpho_fields[2:]
        return self

    def __repr__(self):
        repr_str = '{}:{}:{}'.format(self.form, self.lemma, ':'.join(self.interp))
        if self.unknown_form:
            repr_str = '??_' + repr_str
        elif self.corrected:
            repr_str = '!!_' + repr_str
        if self.proper_name:
            repr_str = 'PN_' + repr_str
        if self.latin:
            repr_str = 'LA_' + repr_str
        return repr_str

    def interp_str(self):
        return ':'.join(self.interp)
