from x86ast import *

EAX = Reg86('eax')
EBX = Reg86('ebx')
ECX = Reg86('ecx')
EDX = Reg86('edx')
ESI = Reg86('esi')
EDI = Reg86('edi')
EBP = Reg86('ebp')
ESP = Reg86('esp')

def name(val):
    if isinstance(val, Var86):
        return val.name
    elif isinstance(val, Reg86):
        return val.register
    else: raise Exception('Attempting to get name of invalid argument ' + str(val))

regcolors = {
    name(EAX) : 0,
    name(EBX) : 1,
    name(ECX) : 2,
    name(EDX) : 3,
    name(ESI) : 4,
    name(EDI) : 5
    }

coloredregs = [EAX, EBX, ECX, EDX, ESI, EDI]

memlocs = 0

temp_counter = -1
def new_temp(prefix):
    global temp_counter
    temp_counter = temp_counter + 1
    return prefix + str(temp_counter)

def regalloc(instrs):
    instrs = allocate(instrs, regcolors, [])
    return [Push86(EBP), Move86(ESP, EBP), Sub86(Const86(memlocs * 4), ESP)] + instrs + [Move86(Const86(0), EAX), Leave86(), Ret86()]

def allocate(instrs, colors, unspillable):
#    print 'Instrs:\n', '\n'.join(map(str, instrs))
    (l_before, l_after) = liveness(instrs)
#    print 'L_after:\n', '\n'.join(map(str, l_after))
    igraph = interference(instrs, l_after)
#    print 'Interference:\n', '\n'.join(map(lambda (k,v): '%s = %s' % (str(k), str(v)), igraph.items()))
    colors = color(igraph, colors, unspillable)
#    print 'Coloring:\n', '\n'.join(map(lambda (k,v): '%s = %d' % (str(k), v), colors.items()))
    selected_instrs = location_select(instrs, colors)
    spill_lines = spills(selected_instrs)
    if spill_lines:
        (new_instrs, new_unspillable) = generate_spills(instrs, spill_lines)
        colors = dict(regcolors.items() + filter(lambda (k,v): v > 5, colors.items()))
        return allocate(new_instrs, colors, new_unspillable + unspillable)
    else: return filter(lambda instr: not trivial(instr), selected_instrs)
    
def liveness(instrs):
    def add_varreg(val, lst):
        if isinstance(val, Var86) or isinstance(val, Reg86):
            lst.add(name(val))
    def try_remove(val, lst):
        if (isinstance(val, Var86) or isinstance(val, Reg86)) and name(val) in lst:
            lst.remove(name(val))
    def liveness_analysis(instrs, current_live):
        liveness = []
        for instr in instrs:
            if isinstance(instr, Add86) or isinstance(instr, Sub86):
                add_varreg(instr.value, current_live)
                add_varreg(instr.target, current_live)
            elif isinstance(instr, Move86):
                try_remove(instr.target, current_live)
                add_varreg(instr.value, current_live)
            elif isinstance(instr, Push86):
                add_varreg(instr.value, current_live)
            elif isinstance(instr, Neg86):
                add_varreg(instr.target, current_live)
            elif isinstance(instr, Call86):
                try_remove(EAX, current_live)
                try_remove(ECX, current_live)
                try_remove(EDX, current_live)
            liveness += [current_live.copy()]
        return liveness
    instrs = instrs[:]
    instrs.reverse()
    l_before = liveness_analysis(instrs, set([]))
    l_before.reverse()
    l_after = l_before[1:]
    l_after.append(set([]))
    return (l_before, l_after)

def interference(instrs, l_after):
    igraph = { 'eax' : set([]), 'ecx' : set([]), 'edx' : set([]) }
    def valid_node(v):
        return isinstance(v, Reg86) or isinstance(v, Var86)
    def add_edge(t, s):
        igraph[t].add(s)
        igraph[s].add(t)
    for instr in instrs:
        if isinstance(instr, Move86) or isinstance(instr, Add86) or isinstance(instr, Sub86):
            if valid_node(instr.value):
                igraph[name(instr.value)] = set([])
            if valid_node(instr.target):
                igraph[name(instr.target)] = set([])
        if isinstance(instr, Push86):
            if valid_node(instr.value):
                igraph[name(instr.value)] = set([])
        if isinstance(instr, Neg86):
            if valid_node(instr.target):
                igraph[name(instr.target)] = set([])
    for (instr, live) in zip(instrs, l_after):
        if isinstance(instr, Move86) and valid_node(instr.target) and name(instr.target) in live:
            for v in live:
                if v != name(instr.target) and ((not valid_node(instr.value)) or v != name(instr.value)):
                    add_edge(name(instr.target), v)
        elif (isinstance(instr, Add86) or isinstance(instr, Sub86) or isinstance(instr, Neg86)) and valid_node(instr.target) and name(instr.target) in live:
            for v in live:
                if v != name(instr.target):
                    add_edge(name(instr.target), v)
        elif isinstance(instr, Push86) and valid_node(instr.value):
            for v in live:
                if v != name(instr.value):
                    add_edge(name(instr.value), v)
        elif isinstance(instr, Call86):
            for v in live:
                if v != name(EAX):
                    add_edge(name(EAX), v)
                if v != name(ECX):
                    add_edge(name(ECX), v)
                if v != name(EDX):
                    add_edge(name(EDX), v)
    return igraph

def color(igraph, colors, unspillable):
    colors = colors.copy()
    saturations = {}
    for u in igraph.keys():
        if not (u in colors):
            colors[u] = None
    for u in igraph.keys():
        saturations[u] = len(set(filter(lambda c: c != None, map(lambda v: colors[v], list(igraph[u]))))) + (len(igraph.keys()) if u in unspillable else 0)
    w = filter(lambda u: colors[u] == None, igraph.keys())
    while len(w) > 0:
        u = w[0]
        for v in w[1:]:
            if saturations[v] > saturations[u] or (saturations[u] == saturations[v] and v in unspillable):
                u = v
        adj = map(lambda v: colors[v], list(igraph[u]))
        color = 0
        while color in adj:
            color += 1
        colors[u] = color
        for v in igraph[u]:
            saturations[v] = len(set(filter(lambda c: c != None, map(lambda y: colors[y], list(igraph[v])))))
        w.remove(u)
    return colors

def location_select(instrs, colors):
    global memlocs
    memlocs = 0
    def select_location(color):
        global memlocs
        if color < 0:
            raise Exception('Negative color')
        elif color < 6:
            return coloredregs[color]
        else:
            memloc = color - 5
            if memloc > memlocs:
                memlocs = memloc
            return Mem86(memloc * 4, EBP)
    def arg_select(arg):
        if isinstance(arg, Var86):
            return select_location(colors[name(arg)])
        else: return arg
    def instr_select(instr):
        if isinstance(instr, Move86):
            return Move86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, Add86):
            return Add86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, Sub86):
            return Sub86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, Neg86):
            return Neg86(arg_select(instr.target))
        elif isinstance(instr, Push86):
            return Push86(arg_select(instr.value))
        else: return instr
    return map(instr_select, instrs)

def spills(instrs):
    spill_lines = []
    for i in xrange(len(instrs)):
        instr = instrs[i]
        binary = isinstance(instr, Move86) or isinstance(instr, Add86) or isinstance(instr, Sub86)
        if binary and isinstance(instr.value, Mem86) and isinstance(instr.target, Mem86) and instr.target != instr.value:
            spill_lines.append(i)
    return spill_lines

def generate_spills(instrs, spill_lines):
    instrs = instrs[:]
    unspillables = []
    offset = 0
    for i in spill_lines:
        i += offset
        temp = new_temp('spill')
        lhs = instrs[i].value
        instrs[i].value = Var86(temp)
        instrs.insert(i, Move86(lhs, Var86(temp)))
        unspillables.append(temp)
        offset += 1
    return instrs, unspillables

def trivial(instr):
    return isinstance(instr, Move86) and instr.target == instr.value
