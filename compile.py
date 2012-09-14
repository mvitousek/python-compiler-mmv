#!/usr/bin/python

import compiler, sys, os, parse
from compiler.ast import *
#from compiler.visitor import ASTVisitor
from x86ast import *

temp_counter = -1
def new_temp(prefix):
    global temp_counter
    temp_counter = temp_counter + 1
    return prefix + str(temp_counter)

def is_leaf(ast):
    return isinstance(ast, Const) or isinstance(ast, Name)

def flatten(ast):
    if isinstance(ast, Module):
        return Module(ast.doc, flatten(ast.node))
    elif isinstance(ast, Stmt):
        nodes = map(flatten, ast.nodes)
        nodes = sum(nodes, [])
        return Stmt(nodes)
    elif isinstance(ast, Printnl):
        nodes = map(flatten, ast.nodes)
        prints = []
        for (t,l) in nodes:
            if not is_leaf(t):
                temp = new_temp('print')
                l.append(Assign([AssName(temp, 'OP_ASSIGN')], t))
                prints.append(Name(temp))
            else:
                prints.append(t)
        stmts = sum([l for (t, l) in nodes], [])
        return stmts + [Printnl(prints, ast.dest)]
    elif isinstance(ast, Assign):
        nodes = map(flatten, ast.nodes)
        assigns = [t for (t, l) in nodes]
        stmts = sum([l for (t, l) in nodes], [])
        targ_node, targ_stmts = flatten(ast.expr)
        return stmts + targ_stmts + [Assign(assigns, targ_node)]
    elif isinstance(ast, AssName):
        return (ast, [])
    elif isinstance(ast, Discard):
        expr, stmts = flatten(ast.expr)
        return stmts + [Discard(expr)]
    elif isinstance(ast, Const):
        return (ast, [])
    elif isinstance(ast, Name):
        return (ast, [])
    elif isinstance(ast, Add):
        lexpr, lstmts = flatten(ast.left)
        rexpr, rstmts = flatten(ast.right)
        if not is_leaf(lexpr):
            temp = new_temp("left")
            lstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], lexpr))
            lexpr = Name(temp)
        if not is_leaf(rexpr):
            temp = new_temp("right")
            rstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], rexpr))
            rexpr = Name(temp)
        return (Add((lexpr, rexpr)), lstmts + rstmts)
    elif isinstance(ast, UnarySub):
        expr, stmts = flatten(ast.expr)
        if not is_leaf(expr):
            temp = new_temp("usub")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        return (UnarySub(expr), stmts)
    elif isinstance(ast, CallFunc):
        expr, stmts = flatten(ast.node)
        if not is_leaf(expr):
            temp = new_temp("func")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        args_exprs = []
        args_stmts = []
        for arg in ast.args:
            arg_expr, arg_stmts = flatten(arg)
            if not is_leaf(arg_expr):
                temp = new_temp("arg")
                arg_stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], arg_expr))
                arg_expr = Name(temp)
            args_exprs.append(arg_expr)
            args_stmts = args_stmts + arg_stmts
        return (CallFunc(expr, args_exprs), stmts + args_stmts)

def scan_allocs(ast):
    if isinstance(ast, Module):
        return scan_allocs(ast.node)
    elif isinstance(ast, Stmt):
        return reduce(lambda x,y: x.union(y), map(scan_allocs, ast.nodes), set([]))
    elif isinstance(ast, Assign):
        return reduce(lambda x,y: x.union(y), map(scan_allocs, ast.nodes), set([]))
    elif isinstance(ast, AssName):
        return set([ast.name])
    else:
        return set([])

current_offset = 0
stack_map = {}
def allocate(var, size):
    global current_offset, stack_map
    if var in stack_map:
        return stack_map[var]
    current_offset = size + current_offset
    stack_map[var] = current_offset
    return current_offset

EAX = Reg86('eax')
EBP = Reg86('ebp')
ESP = Reg86('esp')

def instr_select(ast, value_mode=Move86):
    global stack_map
    if isinstance(ast, Module):
        return [Push86(EBP), Move86(ESP, EBP), Sub86(Const86(len(scan_allocs(ast)) * 4), ESP)] + instr_select(ast.node) + [Move86(Const86(0), EAX), Leave86(), Ret86()]
    elif isinstance(ast, Stmt):
        return sum(map(instr_select, ast.nodes),[])
    elif isinstance(ast, Printnl):
        return instr_select(ast.nodes[0]) + [Push86(EAX), Call86('print_int_nl'), Add86(Const86(4), ESP)]
    elif isinstance(ast, Assign):
        expr_assemb = instr_select(ast.expr)
        offset = allocate(ast.nodes[0].name, 4)
        return expr_assemb + [Move86(EAX, Mem86(offset, EBP))]
    elif isinstance(ast, Discard):
        return instr_select(ast.expr)
    elif isinstance(ast, Add):
        return instr_select(ast.left) + instr_select(ast.right, value_mode=Add86)
    elif isinstance(ast, UnarySub):
        return instr_select(ast.expr) + [Neg86(EAX)]
    elif isinstance(ast, CallFunc):
        return [Call86('input')]
    elif isinstance(ast, Const):
        return [value_mode(Const86(ast.value), EAX)]
    elif isinstance(ast, Name):
        return [value_mode(Mem86(stack_map[ast.name], EBP), EAX)]
    else:
        raise Exception("Unexpected term: " + str(ast))

def compile_string(s):
    ast = parse.parse(s)
    fast = flatten(ast)
    assembly = instr_select(fast)

    print '.globl main\nmain:\n\t' + '\n\t'.join(map(str,assembly)) + '\n'

def compile_file(file_name, output_name):
    input_file = open(file_name)
    source = input_file.read()
    input_file.close()

    ast = parse.parse(source)
    fast = flatten(ast)
    
    assembly = instr_select(fast)
    assembly = '.globl main\nmain:\n\t' + '\n\t'.join(map(str,assembly)) + '\n'
    
    output_file = open(output_name, 'w+')
    output_file.write(assembly)
    output_file.close()

files = []
strings = []
assemble = False
execute = False
string = False
for i in xrange(1, len(sys.argv)):
    opt = sys.argv[i]
    if string:
        strings.append(opt)
        string = False
    elif opt == '-s':
        string = True
    elif opt == '-a':
        assemble = True
    elif opt == '-e':
        assemble = execute = True
    else: files.append(opt)

for input_string in strings:
    compile_string(input_string)

for input_name in files:
    name_split = input_name.split('.')
    base_name = '.'.join(name_split[0:len(name_split)-1])
    output_name = base_name + '.s'
    compile_file(input_name, output_name)
    if assemble:
        os.system(('gcc -m32 -o %s.out %s *.o -lm' % (base_name, output_name)))
    if execute:
        os.system(('./%s.out' % base_name))
