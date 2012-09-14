reserved = {
    'print' : 'PRINT'
    }

tokens = [
    'INT', 
    'ADD',
    'SUB',
    'NAME', 
    'LPAREN', 
    'RPAREN', 
    'NL', 
    'EQ'
    ] + list(reserved.values())

t_ignore = ' \t'
t_ignore_COMMENT = r'\#[^\n]*'

def t_error(t):
    print 'illegal character: %s' % t.value[0]

def t_INT(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        print 'integer value too large', t.value
        t.value = 0
    return t

def t_NL(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')
    return t

def t_NAME(t):
    r'[a-zA-Z_]\w*'
    t.type = reserved.get(t.value, 'NAME')
    return t

t_ADD = r'\+'
t_SUB = r'\-'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_EQ = r'='

import ply.lex as lex
lex.lex()
