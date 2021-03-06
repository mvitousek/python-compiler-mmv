class X86Arg:
    def __str__(self):
        return self.mnemonic()
    def __repr__(self):
        return self.mnemonic()
    def __hash__(self):
        return hash(self.__str__())
    def __eq__(self, that):
        return self.mnemonic() == that.mnemonic()
    
class Const86(X86Arg):
    def __init__(self, value):
        self.value = value
    def mnemonic(self):
        return '$' + str(self.value)

class Reg86(X86Arg):
    def __init__(self, register):
        self.register = register
    def mnemonic(self):
        return '%' + self.register

class Mem86(X86Arg):
    def __init__(self, offset, arg):
        self.offset = offset
        self.arg = arg
    def mnemonic(self):
        return ('-%d(%s)' % (self.offset, self.arg.mnemonic()))

class Var86(X86Arg):
    def __init__(self, name):
        self.name = name
    def mnemonic(self):
        return self.name

class X86Inst:
    def __str__(self):
        return self.mnemonic()
    def __repr__(self):
        return self.mnemonic()

class Push86(X86Inst):
    def __init__(self, value):
        self.value = value
    def mnemonic(self):
        return 'pushl ' + self.value.mnemonic() 

class Move86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('movl %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))

class Sub86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('subl %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))

class Add86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('addl %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))

class Neg86(X86Inst):
    def __init__(self, target):
        self.target = target
    def mnemonic(self):
        return 'negl ' + self.target.mnemonic()

class Not86(X86Inst):
    def __init__(self, target):
        self.target = target
    def mnemonic(self):
        return 'notl ' + self.target.mnemonic()

class Call86(X86Inst):
    def __init__(self, function):
        self.function = function
    def mnemonic(self):
        return 'call ' + self.function

class LShift86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('sall %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))

class RShift86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('sarl %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))    

class Or86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('orl %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))

class And86(X86Inst):
    def __init__(self, value, target):
        self.value = value
        self.target = target
    def mnemonic(self):
        return ('andl %s, %s' % (self.value.mnemonic(), self.target.mnemonic()))

class Comp86(X86Inst):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def mnemonic(self):
        return ('cmpl %s, %s' % (self.left.mnemonic(), self.right.mnemonic()))

class SetEq86(X86Inst):
    def __init__(self, target):
        self.target = target
    def mnemonic(self):
        return ('sete %s' % self.target.mnemonic())

class SetNEq86(X86Inst):
    def __init__(self, target):
        self.target = target
    def mnemonic(self):
        return ('setne %s' % self.target.mnemonic())

class Jump86(X86Inst):
    def __init__(self, target):
        self.target = target
    def mnemonic(self):
        return ('jmp %s' % self.target)

class JumpIf86(X86Inst):
    def __init__(self, target):
        self.target = target
    def mnemonic(self):
        return ('je %s' % self.target)

class Label86(X86Inst):
    def __init__(self, name):
        self.name = name
    def mnemonic(self):
        return self.name + ':'

class If86(X86Inst):
    def __init__(self, then, else_):
        self.then = then
        self.else_ = else_
    def mnemonic(self):
        return 'if:\n' + '\n'.join(map(lambda x: x.mnemonic(), self.then)) + '\nelse:\n' + '\n'.join(map(lambda x: x.mnemonic(), self.else_))

class Leave86(X86Inst):
    def mnemonic(self):
        return 'leave'

class Ret86(X86Inst):
    def mnemonic(self):
        return 'ret'
