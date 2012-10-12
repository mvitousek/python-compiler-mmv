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
    l_after = liveness(instrs)
    print 'L_after:\n', '\n'.join(map(str, l_after))
    igraph = interference(l_after)
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
            if isinstance(instr, Add86) or isinstance(instr, Sub86) or isinstance(instr, And86) or isinstance(instr, Or86) or isinstance(instr, LShift86) or isinstance(instr, RShift86):
                add_varreg(instr.value, current_live)
                add_varreg(instr.target, current_live)
            elif isinstance(instr, Move86):
                try_remove(instr.target, current_live)
                add_varreg(instr.value, current_live)
            elif isinstance(instr, Push86):
                add_varreg(instr.value, current_live)
            elif isinstance(instr, Neg86) or isinstance(instr, Not86):
                add_varreg(instr.target, current_live)
            elif isinstance(instr, Call86):
                try_remove(EAX, current_live)
                try_remove(ECX, current_live)
                try_remove(EDX, current_live)
            elif isinstance(instr, Comp86):
                add_varreg(instr.left, current_live)
                add_varreg(instr.right, current_live)
            elif isinstance(instr, SetEq86):
                try_remove(EAX, current_live)
            elif isinstance(instr, SetNEq86):
                try_remove(EAX, current_live)
            elif isinstance(instr, If86):
                then = instr.then[:]
                then.reverse()
                else_ = instr.else_[:]
                else_.reverse()
                thenbefore = liveness_analysis(then, current_live.copy())
                elsebefore = liveness_analysis(else_, current_live.copy())
                thenbefore.reverse()
                elsebefore.reverse()
                current_live = thenbefore[0][1] | elsebefore[0][1] 
                liveness += [[thenbefore, elsebefore, current_live.copy()]]
                continue
            liveness += [[instr, current_live.copy()]]
        return liveness
    instrs = instrs[:]
    instrs.reverse()
    l_before = liveness_analysis(instrs, set([]))
    def make_after(l_before, initlast):
        last = initlast
        for i in xrange(len(l_before)):
            instr = l_before[i]
            if isinstance(instr[0], list):
                then_after = make_after(instr[0], last)
                else_after = make_after(instr[1], last)
                last = instr[2]
            else:
                temp = l_before[i][1]
                l_before[i][1] = last
                last = temp
    make_after(l_before, set([]))
    l_before.reverse()
    return l_before

def interference(l_after):
    igraph = { 'eax' : set([]), 'ecx' : set([]), 'edx' : set([]) }
    def valid_node(v):
        return isinstance(v, Reg86) or isinstance(v, Var86)
    def add_edge(t, s):
        igraph[t].add(s)
        igraph[s].add(t)
    def fill_igraph(live_vars, igraph):
        for live in live_vars:
            if isinstance(live[0], list):
                fill_igraph(live[0], igraph)
                fill_igraph(live[1], igraph)
            else:
                for v in live[1]:
                    igraph[v] = set([])
    fill_igraph(l_after, igraph)
    for inslive in l_after:
        instr = inslive[0]
        live = inslive[1]
        if isinstance(instr, Move86) and valid_node(instr.target) and name(instr.target) in live:
            for v in live:
                if v != name(instr.target) and ((not valid_node(instr.value)) or v != name(instr.value)):
                    add_edge(name(instr.target), v)
        elif (isinstance(instr, Add86) or isinstance(instr, Sub86) or isinstance(instr, Neg86) or isinstance(instr, Not86) or isinstance(instr, And86) or isinstance(instr, Or86) or isinstance(instr, LShift86) or isinstance(instr, RShift86)) and valid_node(instr.target) and name(instr.target) in live:
            for v in live:
                if v != name(instr.target):
                    add_edge(name(instr.target), v)
        elif isinstance(instr, Comp86):
            for v in live:
                if valid_node(instr.left) and v != name(instr.left):
                    add_edge(name(instr.left), v)
                if valid_node(instr.right) and v != name(instr.right):
                    add_edge(name(instr.right), v)
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
        elif isinstance(instr, list):
            thenlive, elselive, live = inslive
            then_igraph = interference(thenlive)
            else_igraph = interference(elselive)
            for v in then_igraph:
                if v in igraph:
                    igraph[v] = igraph[v] | then_igraph[v]
            for v in else_igraph:
                if v in igraph:
                    igraph[v] = igraph[v] | else_igraph[v]
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
            try:
                return select_location(colors[name(arg)])
            except KeyError:
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
        elif isinstance(instr, Not86):
            return Not86(arg_select(instr.target))
        elif isinstance(instr, Push86):
            return Push86(arg_select(instr.value))
        elif isinstance(instr, And86):
            return And86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, Or86):
            return Or86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, LShift86):
            return LShift86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, RShift86):
            return RShift86(arg_select(instr.value), arg_select(instr.target))
        elif isinstance(instr, Comp86):
            return Comp86(arg_select(instr.left), arg_select(instr.right))
        elif isinstance(instr, SetEq86):
            return SetEq86(arg_select(instr.target))
        elif isinstance(instr, SetNEq86):
            return SetNEq86(arg_select(instr.target))
        elif isinstance(instr, If86):
            return If86(location_select(instr.then, colors), location_select(instr.else_, colors))
        else: return instr
    return map(instr_select, instrs)

def spills(instrs):
    spill_lines = []
    for i in xrange(len(instrs)):
        instr = instrs[i]
        binary = isinstance(instr, Move86) or isinstance(instr, Add86) or isinstance(instr, Sub86) or isinstance(instr, And86) or isinstance(instr, Or86) or isinstance(instr, LShift86) or isinstance(instr, RShift86)
        if binary and isinstance(instr.value, Mem86) and isinstance(instr.target, Mem86):
            spill_lines.append(i)
        elif isinstance(instr, Comp86) and isinstance(instr.left, Mem86) and isinstance(instr.right, Mem86):
            spill_lines.append(i) 
    return spill_lines

def generate_spills(instrs, spill_lines):
    instrs = instrs[:]
    unspillables = []
    offset = 0
    for i in spill_lines:
        i += offset
        temp = new_temp('spill')
        if isinstance(instrs[i], Comp86):
            lhs = instrs[i].left
            instrs[i].left = Var86(temp)
        else:
            lhs = instrs[i].value
            instrs[i].value = Var86(temp)
        instrs.insert(i, Move86(lhs, Var86(temp)))
        unspillables.append(temp)
        offset += 1
    return instrs, unspillables

def trivial(instr):
    return isinstance(instr, Move86) and instr.target == instr.value
