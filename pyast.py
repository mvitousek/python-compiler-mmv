class GetTag:
    def __init__(self, expr):
        self.expr = expr
    def __repr__(self):
        return 'GetTag(%s)' % self.expr
class ProjectTo:
    def __init__(self, typ, expr):
        self.expr = expr
        self.type = typ
    def __repr__(self):
        return 'ProjectTo(%s,%s)' % (self.type, self.expr)
class InjectFrom:
    def __init__(self, typ, expr):
        self.expr = expr
        self.type = typ
    def __repr__(self):
        return 'InjectFrom(%s,%s)' % (self.type, self.expr)
class Let:
    def __init__(self, name, rhs, body):
        self.name = name
        self.rhs = rhs
        self.body = body
    def __repr__(self):
        return 'Let(%s,%s,%s)' % (self.name, self.rhs, self.body)
class IfStmt:
    def __init__(self, test, then, else_):
        self.test = test
        self.then = then
        self.else_ = else_
    def __repr__(self):
        return 'IfStmt(%s,%s,%s)' % (self.test, self.then, self.else_)
