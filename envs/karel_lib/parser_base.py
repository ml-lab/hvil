from __future__ import print_function

import numpy as np
import random
import ply.lex as lex
from functools import wraps
from collections import defaultdict

from  . import yacc
from .karel_runtime import KarelRuntime
from .utils import TimeoutError
from .utils import get_rng
from .utils import pprint
from .utils import str2bool
from .utils import timeout

class Parser(object):
    """
    Base class for a lexer/parser that has the rules defined as methods.
    """
    tokens = ()
    precedence = ()

    def __init__(self,
                 rng=None,
                 min_int=0,
                 max_int=19,
                 debug=False,
                 build_tree=False,
                 **kwargs):
        self.names = {}
        self.debug = debug

        # Build the lexer and parser
        modname = self.__class__.__name__

        self.lexer = lex.lex(module=self, debug=self.debug)

        self.yacc, self.grammar = yacc.yacc(
                module=self,
                debug=self.debug,
                tabmodule="_parsetab",
                with_grammar=True)

        self.prodnames = self.grammar.Prodnames

        #########
        # main
        #########

        self.debug = debug
        self.min_int = min_int
        self.max_int = max_int
        self.build_tree = build_tree
        self.int_range = list(range(min_int, max_int+1))

        int_tokens = ['INT{}'.format(num) for num in self.int_range]
        self.tokens_details = list(set(self.tokens) - set(['INT'])) + int_tokens

        self.tokens_details.sort()
        self.tokens_details = ['END'] + self.tokens_details

        self.idx_to_token_details = {
                idx: token for idx, token in enumerate(self.tokens_details) }
        self.token_to_idx_details = {
                token:idx for idx, token in self.idx_to_token_details.items() }

        self.rng = get_rng(rng)
        self.karel = KarelRuntime()

    def lex_to_idx(self, code, details=False):
        tokens = []
        self.lexer.input(code)
        while True:
            tok = self.lexer.token()
            if not tok:
                break

            if details:
                if tok.type == 'INT':
                    idx = self.token_to_idx_details["INT{}".format(tok.value)]
                else:
                    idx = self.token_to_idx_details[tok.type]
            else:
                idx = self.token_to_idx[tok.type]
            tokens.append(idx)
        return tokens


    #########
    # Karel
    #########

    def get_state(self):
        return self.karel.state

    def parse(self, code,  **kwargs):
        if isinstance(code, (list, tuple)):
            return self.yacc.parse(None,
                    tokenfunc=self.token_list_to_tokenfunc(code), **kwargs)
        else:
            return self.yacc.parse(code, **kwargs)

    def run(self, code, **kwargs):
        return self.parse(code, **kwargs)()

    def draw(self, *args, **kwargs):
        return self.karel.draw(*args, **kwargs)

    def draw_for_tensorboard(self):
        return "\t" + "\n\t".join(self.draw(no_print=True))

    def flush_hit_info(self):
        self.hit_info = None

def parser_prompt(parser):
    import argparse
    from prompt_toolkit import prompt
    from prompt_toolkit.token import Token

    def continuation_tokens(cli, width):
        return [(Token, ' ' * (width - 5) + '.' * 3 + ':')]

    def is_multi_line(line):
        return line.strip()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--debug', type=str2bool, default=False)
    arg_parser.add_argument('--world', type=str, default=None, help='Path to world text file')
    arg_parser.add_argument('--world_height', type=int, default=8, help='Height of square grid world')
    arg_parser.add_argument('--world_width', type=int, default=8, help='Width of square grid world')
    args = arg_parser.parse_args()

    line_no = 1
    parser.debug = args.debug

    print('Press [Meta+Enter] or [Esc] followed by [Enter] to accept input.')
    while True:
        code = prompt(u'In [{}]: '.format(line_no), multiline=True,
                      get_continuation_tokens=continuation_tokens)

        if args.world is not None:
            parser.new_game(world_path=args.world)
        else:
            parser.new_game(world_size=(args.world_width, args.world_height))

        print('Input:')
        parser.draw()
        parser.run(code, debug=False)
        print('Output:')
        parser.draw()
        line_no += 1
