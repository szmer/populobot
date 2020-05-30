from popbot_src.parsed_token import SentenceDAG, ParsedToken

class TestSentenceDAG():
    def test_token_positions(self):
       # The simplest case - linear progression of tokens.
       token1 = ParsedToken('a', 'a', 'a', sentence_starting=True)
       token2 = ParsedToken('b', 'b', 'b')
       token3 = ParsedToken('c', 'c', 'c')
       token1.forward_paths = [token2]
       token2.forward_paths = [token3]
       test_sent1 = SentenceDAG()
       test_sent1.tokens = [token1, token2, token3]
       assert test_sent1.all_paths() == [[token1, token2, token3]]
       assert test_sent1.token_positions() == [token1, token2, token3]
       # Two alternate paths through the middle.
       token1 = ParsedToken('a', 'a', 'a', sentence_starting=True)
       token2 = ParsedToken('b', 'b', 'b')
       token3 = ParsedToken('c', 'c', 'c')
       token4 = ParsedToken('d', 'd', 'd')
       token5 = ParsedToken('e', 'e', 'e')
       token1.forward_paths = [token2, token4]
       token2.forward_paths = [token3]
       token3.forward_paths = [token5]
       token4.forward_paths = [token5]
       test_sent2 = SentenceDAG()
       test_sent2.tokens = [token1, token2, token3, token4, token5]
       assert test_sent2.all_paths() == [[token1, token2, token3, token5],
               [token1, token4, token5]]
       assert test_sent2.token_positions() == [token1, [[token2, token3], token4], token5]
       # Two alternatives both at the beginning and in the end.
       token1 = ParsedToken('a', 'a', 'a', sentence_starting=True)
       token2 = ParsedToken('b', 'b', 'b', sentence_starting=True)
       token3 = ParsedToken('c', 'c', 'c')
       token4 = ParsedToken('d', 'd', 'd')
       token5 = ParsedToken('e', 'e', 'e')
       token1.forward_paths = [token3]
       token2.forward_paths = [token3]
       token3.forward_paths = [token4, token5]
       test_sent3 = SentenceDAG()
       test_sent3.tokens = [token1, token2, token3, token4, token5]
       assert test_sent3.all_paths() == [
               [token1, token3, token4],
               [token1, token3, token5],
               [token2, token3, token4],
               [token2, token3, token5]]
       assert test_sent3.token_positions() == [[token1, token2], token3, [token4, token5]]
