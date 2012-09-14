import ply.yacc as yacc
from compiler.ast import *
from lexer import tokens

precedence = (
    ('left', 'ADD'),
    ('right', 'UNEG'),
    ('nonassoc', 'LPAREN')
    )

def p_module(t):
    'module : stmt_list'
    t[0] = Module(None, Stmt(t[1]))

def p_stmt_list_multi(t):
    'stmt_list : stmt nls stmt_list'
    t[0] = [t[1]] + t[3]

def p_stmt_list_single(t):
    'stmt_list : stmt'
    t[0] = [t[1]]

def p_stmt_list_none(t):
    'stmt_list : empty'
    t[0] = []

def p_print(t):
    'stmt : PRINT expr'
    t[0] = Printnl([t[2]], None)

def p_assign(t):
    'stmt : assignee EQ expr'
    t[0] = Assign(t[1], t[3]) 

def p_discard(t):
    'stmt : expr'
    t[0] = Discard(t[1])

def p_assignee(t):
    'assignee : NAME'
    t[0] = [AssName(t[1], 'OP_ASSIGN')]

def p_int(t):
    'expr : INT'
    t[0] = Const(t[1])

def p_add(t):
    'expr : expr ADD expr'
    t[0] = Add((t[1], t[3]))

def p_name(t):
    'expr : NAME'
    t[0] = Name(t[1])

def p_call(t):
    'expr : expr LPAREN args RPAREN'
    t[0] = CallFunc(t[1], t[3], None, None)

def p_neg(t):
    'expr : SUB expr %prec UNEG'
    t[0] = UnarySub(t[2])

def p_paren(t):
    'expr : LPAREN expr RPAREN'
    t[0] = t[2]

def p_args_none(t):
    'args : empty'
    t[0] = []

def p_empty(t):
    'empty :'
    pass

def p_nls(t):
    'nls : NL mnls'
    pass

def p_mnls_more(t):
    'mnls : nls'
    pass

def p_mnls_none(t):
    'mnls : empty'
    pass

# Error rule for syntax errors
def p_error(p):
    print "Syntax error in input! "+ str(p) + " " + str(yacc.token())

parser = None
def parse(s):
    global parser
    if parser == None:
        parser = yacc.yacc()
    ast = parser.parse(s)
    print ast
    return ast
