import compiler, sys
from compiler.ast import *

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
    current_offset = size + current_offset
    stack_map[var] = current_offset
    return current_offset

def compile_stmt(ast, value_mode='movl'):
    global stack_map
    if isinstance(ast, Module):
        return ['pushl %ebp', 'movl %esp, %ebp', ('subl $%d, %%esp' % (len(scan_allocs(ast)) * 4))] + compile_stmt(ast.node) + ['movl $0, %eax', 'leave', 'ret']
    elif isinstance(ast, Stmt):
        return sum(map(compile_stmt, ast.nodes),[])
    elif isinstance(ast, Printnl):
        return compile_stmt(ast.nodes[0]) + ['pushl %eax', 'call print_int_nl', 'addl $4, %esp']
    elif isinstance(ast, Assign):
        expr_assemb = compile_stmt(ast.expr)
        offset = allocate(ast.nodes[0].name, 4)
        return expr_assemb + [('movl %%eax, -%d(%%ebp)' % offset)]
    elif isinstance(ast, Discard):
        return compile_stmt(ast.expr)
    elif isinstance(ast, Add):
        return compile_stmt(ast.left) + compile_stmt(ast.right, value_mode='addl')
    elif isinstance(ast, UnarySub):
        return ['negl %eax']
    elif isinstance(ast, CallFunc):
        return ['call input']
    elif isinstance(ast, Const):
        return [('%s %d, %%eax' % (value_mode, ast.value))]
    elif isinstance(ast, Name):
        return [('%s -%d(%%ebp), %%eax' % (value_mode, stack_map[ast.name]))]
    else:
        raise Exception("Unexpected term: " + str(ast))

def compile_string(s):
    ast = compiler.parse(s)
    fast = flatten(ast)[0]
    assembly = compile_stmt(fast)
    print '.globl main\nmain:\n\t' + '\n\t'.join(assembly)

def compile_file(file_name):
    output_name = file_name.split('.')
    output_name = '.'.join(output_name[0:len(output_name)-1]) + '.s'
    
    input_file = open(file_name)
    source = input_file.read()
    input_file.close()

    ast = compiler.parse(source)
    fast = flatten(ast)
    assembly = compile_stmt(fast)
    assembly = '.globl main\nmain:\n\t' + '\n\t'.join(assembly)
    
    output_file = open(output_name, 'w+')
    output_file.write(assembly)

def ast_to_source(ast, level):
    if isinstance(ast, Module):
        return ast_to_source(ast.node, level)
    elif isinstance(ast, Stmt):
        return "\n".join(map(lambda x: ast_to_source(x, level), ast.nodes))
    elif isinstance(ast, Printnl):
        return "print " + ", ".join(map(lambda x: ast_to_source(x, level), ast.nodes))
    elif isinstance(ast, Assign):
        return " = ".join(map(lambda x: ast_to_source(x, level), ast.nodes)) + " = " + ast_to_source(ast.expr, level)
    elif isinstance(ast, AssName):
        return ast.name
    elif isinstance(ast, Discard):
        return ast_to_source(ast.expr, level)
    elif isinstance(ast, Const):
        return str(ast.value)
    elif isinstance(ast, Name):
        return ast.name
    elif isinstance(ast, Add):
        return "(" + ast_to_source(ast.left, level) + " + " + ast_to_source(ast.right, level) + ")"
    elif isinstance(ast, UnarySub):
        return "(-" + ast_to_source(ast.expr, level) + ")"
    elif isinstance(ast, CallFunc):
        return ast_to_expr(ast.node, level) + "(" + ", ".join(map(lambda x: ast_to_source(x, level), ast.args)) + ")"
    
compile_file(sys.argv[1])
