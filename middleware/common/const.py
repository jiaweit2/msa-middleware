# -*- coding: utf-8 -*-
"""Module describing constants used in athena_lib package
"""

import copy
import json
import logging
import logging.config
import os
import re
import time
from collections import deque
from threading import Timer

import numpy as np

from middleware.common.name import Name
from middleware.common.utils import *

DEFAULT_FRESHNESS_P = 60

# QUERY REQUESTER CONFIG
DEFAULT_DEADLINE = 360

# VARIABLE TYPES
# CONTENTS = 'CONTENTS'
LABEL = "LABEL"
DECISION = "DECISION"

# VARIABLE VALUE STATUS
UNDECIDED = "undecided"
UNRESOLVABLE = "unresolvable"
OTHERWISE = "otherwise"

# FETCH / PREFETCH
FETCH = 1
PREFETCH = 0

# DECISION MAKER PARAMETERS
DEFAULT_PERIOD = 1
DEFAULT_PROB = 0.5
DEFAULT_COST = 1
# MAX_SIZE = 1000000000
# META_INFO_FREQUENCY = 100

# DECISION MAKER MODE
UNICAST = "UNICAST"
CDN = "CDN"

# ATHENA PARSER GRAMMAR
ATHENA_GRAMMAR = r"""
input: (_NEWLINE | stmt)*

stmt: var "=" label
    | var "=" decision
    | vars "=" label

var : NAME
vars : var "," var ("," var)*

value : SIGNED_NUMBER
    | ESCAPED_STRING
    | BOOLEAN        

label : "Label(" annotator_func "," args "," list_of_list ")"
    | "Label(" annotator_func "," args ", "list_of_list "," NUMBER ")"

annotator_func : CNAME

list_of_list : "[" [list ("," list)*] "]"
list : "[" [var ("," var)*] "]"
args : "[" [arg ("," arg)*] "]"
arg : ( var | SIGNED_NUMBER | ESCAPED_STRING | BOOLEAN )

decision : "Decision(" dict ")"
    | "Decision(" dict ", " NUMBER ")"
coa : value ":" logic_exprs

dict : "{" [coa ("," coa)*] "}"
!math_oper : ("==" | "!=" | ">" | ">=" | "<" | "<=")
!conjunction : ("&" | "|")        

!logic_exprs : logic_expr (conjunction logic_expr)*
    | "otherwise"

!logic_expr : predicate (conjunction predicate)*
    | "(" logic_expr (conjunction logic_expr)* ")"     

predicate : var math_oper value
    | var math_oper var    

COMMENT: /#[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT )+
BOOLEAN: "True" | "False"

NAME: [ "%" | "$" ] ( LETTER | DIGIT | /[u"\u00A0-\u04FF"]/ | "/" | "_" | "." )+

%import common.CNAME
%import common.LETTER
%import common.DIGIT
%import common.ESCAPED_STRING
%import common.NUMBER
%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
"""
