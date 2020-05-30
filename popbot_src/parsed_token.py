class SentenceDAG():
    """
    A Directed Acyclic Graph representing possible paths through the sentence.
    """
    def __init__(self):
        self.tokens = []

    def chosen_tokens(self):
        """
        Get the list of only the tokens chosen in disambiguation, in the right sequence.
        """
        first_token = [tok for tok in self.tokens if tok.sentence_starting and tok.chosen]
        if len(first_token) != 1:
            raise ValueError('Cannot find one first token ({}) in {}'.format(first_token,
                self.tokens))
        result_tokens = first_token
        while result_tokens[-1].forward_paths:
            forward_token = [tok for tok in result_tokens[-1].forward_tokens if tok.chosen]
            if len(forward_token) != 1:
                raise ValueError('Cannot find one first token ({}) in {}'.format(forward_token,
                    result_tokens[-1].forward_tokens))
            result_tokens.append(forward_token[0])
        return result_tokens
    
    def all_paths(self):
        """
        A list of tokens representing all possible paths through the sentence.
        """
        all_paths = [[tok] for tok in self.tokens if tok.sentence_starting]
        while True:
            new_paths = []
            new_added = False
            for path in all_paths:
                for next_tok in path[-1].forward_paths:
                    new_added = True
                    new_paths.append(path + [next_tok])
                if not path[-1].forward_paths: # the path already ended
                    new_paths.append(path)
            if new_added:
                all_paths = new_paths
            else:
                break
        return all_paths

    def token_positions(self):
        """
        Return a list of tokens (or lists representing multiple paths, possibly with sublists -
        paths of many consecutive tokens) representing the whole route through the DAG with edges.
        """
        all_paths = self.all_paths()
        max_path_length = max([len(path) for path in all_paths])

        positions = []
        already_joining = set()#[tok for tok in self.tokens if tok.sentence_starting])
        while True:
            # Find the token where the paths join next.
            tokens_appearances = dict()
            joining_token = None
            for node_n in range(max_path_length):
                for path in all_paths:
                    if node_n < len(path) and not path[node_n] in already_joining:
                        if not path[node_n] in tokens_appearances:
                            tokens_appearances[path[node_n]] = 0
                        tokens_appearances[path[node_n]] += 1
                        # If the token appears in all paths.
                        if tokens_appearances[path[node_n]] == len(all_paths):
                            joining_token = path[node_n]
                            already_joining.add(joining_token)
                            break
                if joining_token is not None:
                    break
            # Add one path, or a choice list leading to the joining token.
            # (First, collect all possible local paths).
            following_paths = []
            print('-------------------------------')
            for path_n, path in enumerate(all_paths):
                local_path = []
                for node_n, node in enumerate(path):
                    # (We want this to always trigger with no joining token, to collect the end
                    # of the sentence)
                    if node != joining_token:
                        local_path.append(node)
                    # NOTE if the is no joining_token, we collect the nodes until the end of the
                    # path.
                    if node == joining_token or (joining_token is None and node_n+1 == len(path)):
                        if len(local_path) == 1:
                            local_path = local_path[0]
                        if local_path and not local_path in following_paths: # can be blank at start
                            following_paths.append(local_path)
                        # Shorten the path, skipping also the joining token.
                        all_paths[path_n] = path[node_n+1:]
                        break
            # (Second, add the local paths to the positions).
            if len(following_paths) == 1:
                if isinstance(following_paths[0], list):
                    raise ValueError('The only path is a list: {}'.format(following_paths[0]))
                if not following_paths[0] in positions:
                    positions.append(following_paths[0])
                    print('added only path', following_paths[0])
            elif following_paths:
                positions.append(following_paths)
                print('added path', following_paths)
            # Always add the joining token as the sole path through its position.
            if joining_token is not None:
                print('added as joining', joining_token)
                positions.append(joining_token)
            # No joining token found is the sign of sentence ending.
            if joining_token is None:
                break
        return positions

class NoneTokenError(Exception):
    pass

class ParsedToken():
    """
    The class for saving parsed tokens obtained by morpho.py.
    """
    def __init__(self, form, lemma, interp,
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
