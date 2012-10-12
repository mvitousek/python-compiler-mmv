#!/usr/bin/python

import compiler, sys, os, parse, regalloc
from compiler.ast import *
#from compiler.visitor import ASTVisitor
from x86ast import *
from regalloc import new_temp
from pyast import *

INT_TAG = Const(0)
BOOL_TAG = Const(1)
BIG_TAG = Const(2)


INT_TAG_COMP = [('==', Const(0))]
BOOL_TAG_COMP = [('==', Const(1))]
BIG_TAG_COMP = [('==', Const(3))]

DYN_ERR = CallFunc(Name('error_pyobj'), [])
INT_ERR = ProjectTo(INT_TAG, DYN_ERR)
BOOL_ERR = ProjectTo(BOOL_TAG, DYN_ERR)
BIG_ERR = ProjectTo(BIG_TAG, DYN_ERR)

def is_leaf(ast):
    return isinstance(ast, Const) or isinstance(ast, Name)


def make_and(nodes, last=BOOL_ERR):
    if nodes:
        node = nodes[0]
        ntemp = Name(new_temp('and'))
        return Let(ntemp, node, IfExp(ntemp,
                                      Compare(ntemp, [('==', Const(0))]),
                                      make_and(nodes[1:], ntemp)))
    else:
        return last
def make_or(nodes, last=BOOL_ERR):
    if nodes:
        node = nodes[0]
        ntemp = Name(new_temp('or'))
        return Let(ntemp, node, IfExp(ntemp,
                                      Compare(ntemp, [('==', Const(1))]),
                                      make_or(nodes[1:], ntemp)))
    else:
        return last


def is_true(n):
    return IfExp(Compare(ProjectTo(BOOL_TAG, n), [('==', Const(1))]),
                 make_or([Compare(GetTag(n), INT_TAG_COMP),
                     Compare(GetTag(n), BOOL_TAG_COMP)]),
                 CallFunc(Name('is_true'), [n]))

def is_false(n):
    return IfExp(Compare(ProjectTo(BOOL_TAG, n), [('==', Const(0))]),
                 make_or([Compare(GetTag(n), INT_TAG_COMP),
                     Compare(GetTag(n), BOOL_TAG_COMP)]),
                 Compare(CallFunc(Name('is_true'), [n]), [('==', Const(0))]))

def explicate(ast):
    if isinstance(ast, Module):
        return Module(ast.doc, explicate(ast.node))
    elif isinstance(ast, Stmt):
        nodes = map(explicate, ast.nodes)
        return Stmt(nodes)
    elif isinstance(ast, Printnl):
        return Printnl(map(explicate, ast.nodes), ast.dest)
    elif isinstance(ast, Assign):
        return Assign(map(explicate, ast.nodes), explicate(ast.expr))
    elif isinstance(ast, Discard):
        return Discard(explicate(ast.expr))
    elif isinstance(ast, Add):
        left = explicate(ast.left)
        right = explicate(ast.right)
        ltemp = Name(new_temp('left'))
        rtemp = Name(new_temp('right'))
        return Let(ltemp,
                   left,
                   Let(rtemp,
                       right,
                       IfExp(InjectFrom(INT_TAG, Add((ProjectTo(INT_TAG, ltemp), ProjectTo(INT_TAG, rtemp)))),
                             make_and([make_or([Compare(GetTag(ltemp),
                                              INT_TAG_COMP),
                                      Compare(GetTag(ltemp),
                                              BOOL_TAG_COMP)]),
                                  make_or([Compare(GetTag(rtemp),
                                              INT_TAG_COMP),
                                      Compare(GetTag(rtemp),
                                              BOOL_TAG_COMP)])]),
                             IfExp(InjectFrom(BIG_TAG, CallFunc(Name('add'),
                                                                [ProjectTo(BIG_TAG, ltemp),
                                                                 ProjectTo(BIG_TAG, rtemp)])),
                                   make_and([Compare(GetTag(ltemp),
                                                BIG_TAG_COMP),
                                        Compare(GetTag(rtemp),
                                                BIG_TAG_COMP)]),
                                   DYN_ERR))))
    elif isinstance(ast, UnarySub):
        expr = explicate(ast.expr)
        temp = Name(new_temp('usub'))
        return Let(temp,
                   expr,
                   IfExp(InjectFrom(INT_TAG, UnarySub(ProjectTo(INT_TAG, temp))),
                         make_or([Compare(GetTag(temp), INT_TAG_COMP),
                             Compare(GetTag(temp), BOOL_TAG_COMP)]),
                         DYN_ERR))
    elif isinstance(ast, Compare):
        expr = explicate(ast.expr)
        op, comp = ast.ops[0]
        comp = explicate(comp)
        etemp = Name(new_temp('expr'))
        ctemp = Name(new_temp('comp'))
        func = Name('equal') if op == '==' else Name('not_equal')
        return Let(etemp,
                   expr,
                   Let(ctemp,
                       comp,
                       IfExp(InjectFrom(BOOL_TAG, 
                                        Compare(ProjectTo(INT_TAG, etemp), 
                                                [(op, ProjectTo(INT_TAG, ctemp))])),
                             make_and([make_or([Compare(GetTag(etemp),
                                              INT_TAG_COMP),
                                      Compare(GetTag(etemp),
                                              BOOL_TAG_COMP)]),
                                  make_or([Compare(GetTag(ctemp),
                                              INT_TAG_COMP),
                                      Compare(GetTag(ctemp),
                                              BOOL_TAG_COMP)])]),
                             IfExp(InjectFrom(BOOL_TAG, CallFunc(Name('equal'),
                                                                 [ProjectTo(BIG_TAG, ltemp),
                                                                  ProjectTo(BIG_TAG, rtemp)])),
                                   make_and([Compare(GetTag(ltemp),
                                                BIG_TAG_COMP),
                                        Compare(GetTag(rtemp),
                                                BIG_TAG_COMP)]),
                                   DYN_ERR))))
    elif isinstance(ast, Or): #(nodes)
        def gen_or(nodes, last):
            if nodes:
                node = explicate(nodes[0])
                ntemp = Name(new_temp('or'))
                return Let(ntemp, node, IfExp(ntemp,
                                              is_true(ntemp),
                                              gen_or(nodes[1:], ntemp)))
            else:
                return last
        return gen_or(ast.nodes, DYN_ERR)
    elif isinstance(ast, And):#(nodes)
        def gen_and(nodes, last):
            if nodes:
                node = explicate(nodes[0])
                ntemp = Name(new_temp('and'))
                return Let(ntemp, node, IfExp(ntemp,
                                              is_false(ntemp),
                                              gen_and(nodes[1:], ntemp)))
            else:
                return last
        return gen_and(ast.nodes, DYN_ERR)
    elif isinstance(ast, Not):#(expr)
        expr = explicate(expr)
        etemp = Name(new_temp('not'))
        return Let(etemp, expr, IfExp(InjectFrom(BOOL_TAG, Compare(ProjectTo(BOOL_TAG, etemp), 
                                                                   [('==', Const(0))])),
                                      make_or(Compare(GetTag(etemp), BOOL_TAG_COMP),
                                         Compare(GetTag(etemp), INT_TAG_COMP)),
                                      InjectFrom(BOOL_TAG, Compare(CallFunc(Name('is_true'),[etemp]),
                                                                   [('==', Const(0))]))))
    elif isinstance(ast, List):#(nodes)
        return List(map(explicate, ast.nodes))
    elif isinstance(ast, Dict):#items
        return Dict(map(lambda p: (p[0], explicate(p[1])), ast.items))
    elif isinstance(ast, Subscript):#expr flags subs
        return Subscript(explicate(ast.expr), ast.flags, map(explicate, ast.subs))
    elif isinstance(ast, IfExp):#test then else_
        return IfExp(explicate(ast.then),
                     ProjectTo(BOOL_TAG, explicate(ast.test)),
                     explicate(ast.else_))
    elif isinstance(ast, Const):
        return InjectFrom(INT_TAG, ast)
    else: return ast

def flatten(ast, extra_flat=False):
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
        targ_node, targ_stmts = flatten(ast.expr, len(filter(lambda x: isinstance(x, Subscript), assigns)))
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
        if not is_leaf(lexpr) or extra_flat:
            temp = new_temp("left")
            lstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], lexpr))
            lexpr = Name(temp)
        if not is_leaf(rexpr) or extra_flat:
            temp = new_temp("right")
            rstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], rexpr))
            rexpr = Name(temp)
        return (Add((lexpr, rexpr)), lstmts + rstmts)
    elif isinstance(ast, Compare):
        lexpr, lstmts = flatten(ast.expr)
        rexpr, rstmts = flatten(ast.ops[0][1])
        if not is_leaf(lexpr) or extra_flat:
            temp = new_temp("left")
            lstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], lexpr))
            lexpr = Name(temp)
        if not is_leaf(rexpr) or extra_flat:
            temp = new_temp("right")
            rstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], rexpr))
            rexpr = Name(temp)
        return (Compare(lexpr, [(ast.ops[0][0], rexpr)]), lstmts + rstmts)
    elif isinstance(ast, Subscript):
        lexpr, lstmts = flatten(ast.expr)
        rexpr, rstmts = flatten(ast.subs[0])
        if not is_leaf(lexpr) or extra_flat:
            temp = new_temp("expr")
            lstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], lexpr))
            lexpr = Name(temp)
        if not is_leaf(rexpr) or extra_flat:
            temp = new_temp("sub")
            rstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], rexpr))
            rexpr = Name(temp)
        return (Compare(lexpr, ast.flags, [rexpr]), lstmts + rstmts)
    elif isinstance(ast, UnarySub):
        expr, stmts = flatten(ast.expr)
        if not is_leaf(expr) or extra_flat:
            temp = new_temp("usub")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        return (UnarySub(expr), stmts)
    elif isinstance(ast, GetTag):
        expr, stmts = flatten(ast.expr)
        if not isinstance(expr, Name):
            temp = new_temp("gettag")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        return (GetTag(expr), stmts)
    elif isinstance(ast, InjectFrom):
        expr, stmts = flatten(ast.expr)
        if not isinstance(expr, Name):
            temp = new_temp("inject")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        return (InjectFrom(ast.type, expr), stmts)
    elif isinstance(ast, ProjectTo):
        expr, stmts = flatten(ast.expr)
        if not isinstance(expr, Name):
            temp = new_temp("project")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        return (ProjectTo(ast.type, expr), stmts)
    elif isinstance(ast, Let):
        expr, stmts = flatten(ast.rhs)
        rest_expr, rest_stmts = flatten(ast.body)
        return (rest_expr, stmts + [Assign([AssName(ast.name.name, 'OP_ASSIGN')], expr)] + rest_stmts)
    elif isinstance(ast, CallFunc):
        expr, stmts = flatten(ast.node)
        if not is_leaf(expr) or extra_flat:
            temp = new_temp("func")
            stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], expr))
            expr = Name(temp)
        args_exprs = []
        args_stmts = []
        for arg in ast.args:
            arg_expr, arg_stmts = flatten(arg)
            if not is_leaf(arg_expr) or extra_flat:
                temp = new_temp("arg")
                arg_stmts.append(Assign([AssName(temp, 'OP_ASSIGN')], arg_expr))
                arg_expr = Name(temp)
            args_exprs.append(arg_expr)
            args_stmts = args_stmts + arg_stmts
        return (CallFunc(expr, args_exprs), stmts + args_stmts)
    elif isinstance(ast, IfExp):
        ftemp = new_temp('if')
        test, tstmts = flatten(ast.then)
        if not is_leaf(test) or extra_flat:
            temp = new_temp("test")
            tstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], test))
            test = Name(temp)
        trexpr, trstmts = flatten(ast.test)
        fexpr, fstmts = flatten(ast.else_)
        trstmts.append(Assign([AssName(ftemp, 'OP_ASSIGN')], trexpr))
        fstmts.append(Assign([AssName(ftemp, 'OP_ASSIGN')], fexpr))
        return (Name(ftemp), tstmts + [IfStmt(test, Stmt(trstmts), Stmt(fstmts))])
    elif isinstance(ast, List):
        lname = new_temp('list')
        stmts = []
        adds = []
        lenname = new_temp('len')
        list_len = InjectFrom(INT_TAG, Const(len(ast.nodes)))
        for i in xrange(len(ast.nodes)):
            node = ast.nodes[i]
            nexpr, nstmts = flatten(node)
            if not is_leaf(nexpr) or extra_flat:
                temp = new_temp("item")
                nstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], nexpr))
                nexpr = Name(temp)
            temp = new_temp('index' + str(i))
            nstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], InjectFrom(INT_TAG, Const(i))))
            stmts = stmts + nstmts
            adds.append(CallFunc(Name('set_subscript'), [Name(lname), Name(temp), nexpr]))
        return (Name(lname), [Assign([AssName(lenname, 'OP_ASSIGN')], list_len),
                              Assign([AssName(lname, 'OP_ASSIGN')], 
                                     CallFunc(Name('create_list'), [Name(lenname)]))] + nstmts + adds)
    elif isinstance(ast, List):
        lname = new_temp('dict')
        stmts = []
        adds = []
        for name, val in ast.items:
            nexpr, nstmts = flatten(name)
            vexpr, vstmts = flatten(val)
            if not is_leaf(nexpr) or extra_flat:
                temp = new_temp("name")
                nstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], nexpr))
                nexpr = Name(temp)
            if not is_leaf(vexpr) or extra_flat:
                temp = new_temp("val")
                vstmts.append(Assign([AssName(temp, 'OP_ASSIGN')], vexpr))
                vexpr = Name(temp)
            stmts = stmts + nstmts + vstmts
            adds.append(CallFunc(Name('set_subscript'), [Name(lname), nexpr, vexpr]))
        return (Name(lname), [Assign([AssName(lname, 'OP_ASSIGN')], 
                                     CallFunc(Name('create_dict'), []))] + nstmts + adds)
    else: raise Exception('Unexpected term to be flattened ' + repr(ast))

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
EBX = Reg86('ebx')
ECX = Reg86('ecx')
EDX = Reg86('edx')
ESI = Reg86('esi')
EDI = Reg86('edi')
EBP = Reg86('ebp')
ESP = Reg86('esp')

def arg_select(ast):
    if isinstance(ast, Name):
        return Var86(ast.name)
    elif isinstance(ast, Const):
        return Const86(ast.value)
    else: raise Exception('unexpected term in argument: ' + repr(ast) + str(type(ast)))

def instr_select(ast, write_target=Var86('discard')):
    global stack_map
    if isinstance(ast, Module):
        return instr_select(ast.node)
    elif isinstance(ast, Stmt):
        return sum(map(instr_select, ast.nodes),[])
    elif isinstance(ast, Printnl):
        return [Push86(arg_select(ast.nodes[0])), Call86('print_any'), Add86(Const86(4), ESP)]
    elif isinstance(ast, Assign):
        if isinstance(ast.nodes[0], AssName):
            return instr_select(ast.expr, Var86(ast.nodes[0].name))
        elif isinstance(ast.nodes[0], Subscript):
            return [Push86(arg_select(ast.nodes[0].expr)), Push86(arg_select(ast.nodes[0].subs[0])),
                    Push86(arg_select(ast.expr)), Call86('set_subscript'), Add86(Const86(12), ESP)]
        else: raise Exception('unexpected assignee ' + str(ast.nodes[0]))
    elif isinstance(ast, Discard):
        return instr_select(ast.expr)
    elif isinstance(ast, Add):
        return [Move86(arg_select(ast.left), write_target), Add86(arg_select(ast.right), write_target)]
    elif isinstance(ast, UnarySub):
        return [Move86(arg_select(ast.expr), write_target), Neg86(write_target)]
    elif isinstance(ast, CallFunc):
        return map(lambda a: Push86(arg_select(a)), ast.args) + [Call86(ast.node.name), 
                                                                 Add86(Const86(4 * len(ast.args)), ESP),
                                                                 Move86(EAX, write_target)]
    elif isinstance(ast, Subscript):
        return [Push86(arg_select(ast.expr)), Push86(arg_select(ast.subs[0])), Call86('get_subscript'),
                Add86(Const(8), ESP), Move86(EAX, write_target)]
    elif isinstance(ast, Compare):
        inst = SetEq86 if ast.ops[0][0] == '==' else SetNEq86
        return [Comp86(arg_select(ast.ops[0][1]), arg_select(ast.expr)), Move86(Const86(0), EAX), 
                inst(Reg86('al')), Move86(EAX, write_target)]
    elif isinstance(ast, IfStmt):
        return [Push86(arg_select(ast.test)), Call86('is_true'), Comp86(Const86(1), EAX), 
                If86(instr_select(ast.then), instr_select(ast.else_))]
    elif isinstance(ast, InjectFrom):
        if ast.type == BIG_TAG:
            tag = arg_select(BIG_TAG)
            return [Move86(tag, write_target), Or86(arg_select(ast.expr), write_target)]
        if ast.type == INT_TAG:
            tag = arg_select(INT_TAG)
        elif ast.type == BOOL_TAG:
            tag = arg_select(BOOL_TAG)
        else: raise Exception('unexpected tag ' + str(ast.type))
        return [LShift86(Const86(2), arg_select(ast.expr)), Move86(tag, write_target), 
                Or86(arg_select(ast.expr), write_target)]
    elif isinstance(ast, ProjectTo):
        if ast.type == BIG_TAG:
            tag = arg_select(BIG_TAG)
            return [Move86(tag, write_target), Not86(write_target), And86(arg_select(ast.expr), write_target)]
        if ast.type == INT_TAG:
            tag = arg_select(INT_TAG)
        elif ast.type == BOOL_TAG:
            tag = arg_select(BOOL_TAG)
        else: raise Exception('unexpected tag ' + str(ast.type))
        return [Move86(arg_select(ast.expr), write_target), RShift86(Const86(2), write_target)]
    elif isinstance(ast, GetTag):
        return [Move86(Const86(3), write_target), And86(arg_select(ast.expr), write_target)]
    elif isinstance(ast, Const):
        return [Move86(Const86(ast.value), write_target)]
    elif isinstance(ast, Name):
        return [Move86(Var86(ast.name), write_target)]
    else:
        raise Exception("Unexpected term: " + str(ast))

def destructure(instrs):
    final_instrs = []
    for instr in instrs:
        if isinstance(instr, If86):
            then = destructure(instr.then)
            else_ = destructure(instr.else_)
            then_label = new_temp('then_branch')
            end_label = new_temp('end_if')
            final_instrs += [JumpIf86(then_label)] + else_ + [Jump86(end_label), Label86(then_label)] + then + [Label86(end_label)]
        else: final_instrs.append(instr)
    return final_instrs

def compile_string(s):
    ast = compiler.parse(s)
    east = explicate(ast)
    print east
    fast = flatten(east)
    print fast
    assembly = instr_select(fast)
    print assembly
    assembly = regalloc.regalloc(assembly)
    assembly = destructure(assembly)
    assembly = '.globl main\nmain:\n\t' + '\n\t'.join(map(str,assembly)) + '\n'

    print assembly

def compile_file(file_name, output_name):
    ast = compiler.parseFile(file_name)
    east = explicate(ast)
    fast = flatten(east)

    assembly = instr_select(fast)
    assembly = regalloc.regalloc(assembly)
    assembly = destructure(assembly)
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




# Liveness analysis
# Lbefore(k)=(Lafter(k) \ Writes(k)) U Reads(k)
# Lafter(k)=Lbefore(k+1)
# Lafter(n)={} when n is final instr
