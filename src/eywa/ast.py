import uuid
from ast import NodeVisitor
from typing import List, Union, Any, Dict, Callable
import eywa.regex as re

class Type(object):
    """
    An Eywa type for a parameter to a function.
    """
    @staticmethod
    def inner(type):
        """
        Look past any type aliases to get the inner type.
        """
        while isinstance(type, Alias):
            type = type.type
        return type


class Void(Type):
    """
    A void type representing no value.
    """
    pass


class Bool(Type):
    """
    A boolean type representing true or false.
    """
    pass


class Char(Type):
    """
    A character type representing a single character.
    """
    pass


class Int(Type):
    """
    An integer type representing an unsigned integer of a given size.
    """

    def __init__(self, size: int = None):
        self.size = size


class String(Type):
    """
    A string type representing a string of a given max length.
    """

    def __init__(self, maxsize: int = 6):
        if maxsize < 0:
            raise Exception('invalid string type')
        self.maxsize = maxsize
        self.char_type = Char()


class Enum(Type):
    """
    An enumeration type representing a choice of values.
    """

    def __init__(self, name: str, values: List[str]):
        self.name = name
        self.values = values


class Array(Type):
    """
    An array type representing an array of a given element type and size.
    """

    def __init__(self, element_type: Type, maxsize: int):
        self.maxsize = maxsize
        self.element_type = element_type


class Struct(Type):
    """
    A struct type representing a struct with a given name and fields.
    """

    def __init__(self, name: str, **kwargs: Type):
        print(kwargs)
        self.name = name
        self.fields = kwargs


class Alias(Type):
    """
    An alias type representing an alias to another type.
    """

    def __init__(self, name: str, type: Type, description=None):
        self.name = name
        self.type = type
        self.description = description


class Expr(object):
    """
    A simple expression class.
    """

    @staticmethod
    def eval(expr, assignment: Dict[str, Any]) -> bool:
        """
        Evaluate an Eywa expression given an assignment of variables.
        """
        return Evaluator(assignment).visit(expr)

    @staticmethod
    def convert(other):
        """
        Ensures that the given object can be converted to an expression.
        """
        if isinstance(other, Expr):
            return other
        if isinstance(other, int):
            return Const(Int(32), other)
        if isinstance(other, Parameter):
            return Var(Type.inner(other.type), other.name)
        raise Exception(f'invalid expression: {other}')

    @staticmethod
    def has_match(type):
        """
        Determines if this expression has a match expression.
        """
        return HasMatch().visit(type)

    def __add__(self, other):
        """
        Override the + operator to create a binary operation expression.
        """
        return Binop(self.type, '+', self, Expr.convert(other))

    def __sub__(self, other):
        """
        Override the - operator to create a binary operation expression.
        """
        return Binop(self.type, '-', self, Expr.convert(other))

    def __and__(self, other):
        """
        Override the & operator to create a binary operation expression.
        """
        return Binop(self.type, '&', self, Expr.convert(other))

    def __or__(self, other):
        """
        Override the | operator to create a binary operation expression.
        """
        return Binop(self.type, '|', self, Expr.convert(other))

    def __le__(self, other):
        """
        Override the <= operator to create a binary operation expression.
        """
        return Binop(Bool(), '<=', self, Expr.convert(other))

    def __lt__(self, other):
        """
        Override the < operator to create a binary operation expression.
        """
        return Binop(Bool(), '<', self, Expr.convert(other))

    def __ge__(self, other):
        """
        Override the >= operator to create a binary operation expression.
        """
        return Binop(Bool(), '>=', self, Expr.convert(other))

    def __gt__(self, other):
        """
        Override the > operator to create a binary operation expression.
        """
        return Binop(Bool(), '>', self, Expr.convert(other))

    def __eq__(self, other):
        """
        Override the == operator to create a binary operation expression.
        """
        return Binop(Bool(), '==', self, Expr.convert(other))

    def __ne__(self, other):
        """
        Override the != operator to create a binary operation expression.
        """
        return Binop(Bool(), '!=', self, Expr.convert(other))

    def get_field(self, field: str):
        """
        A helper function to create a field dereference.
        """
        return Field(self.type.fields[field], self, field)

    def __invert__(self):
        """
        Override the bool operator to create a unary negation expression.
        """
        return Not(Bool(), self)

    def matches(self, regex: re.Regex):
        """
        A helper function to create a match constraint.
        """
        return Match(Bool(), self, regex)

    def forall(self, invariant):
        """
        A helper function to create an array forall expression.
        """
        print("type was:")
        print(self.type)
        return Forall(Bool(), self, invariant)

    def implies(self, other):
        """
        A helper function to create an implies expression.
        """
        return Binop(Bool(), '|', Not(Bool(), self), other)


class Var(Expr):
    """
    A variable expression.
    """

    def __init__(self, type, parameter_name):
        self.type = type
        self.parameter_name = parameter_name


class Const(Expr):
    """
    A constant expression.
    """

    def __init__(self, type, constant):
        if isinstance(type, String) and not isinstance(constant, str):
            raise Exception('Constant expression type mismatch')
        if isinstance(type, Int) and not isinstance(constant, int):
            raise Exception('Constant expression type mismatch')
        self.type = type
        self.constant = constant


class Not(Expr):
    """
    A not expression.
    """

    def __init__(self, type, expr: Expr):
        if not isinstance(type, Bool):
            raise Exception('Not expression expected bool return type')
        self.type = type
        self.expr = expr


class Match(Expr):
    """
    A expr for a regular expression match.
    """

    def __init__(self, type, expr: Expr, regex: re.Regex):
        if not isinstance(type, Bool):
            raise Exception('Match expression expected bool return type')
        if not isinstance(expr.type, String):
            raise Exception('Match expression expected string type')
        self.type = type
        self.expr = expr
        self.regex = regex


class Binop(Expr):
    """
    A binary operation expression.
    """

    def __init__(self, type, op: str, left: Expr, right: Expr):
        self.type = type
        self.op = op
        self.left = left
        self.right = right


class Field(Expr):
    """
    A field dereference expression.
    """

    def __init__(self, type, expr: Expr, field: str):
        if not isinstance(expr.type, Struct):
            raise Exception('Field expression expected struct type')
        if type != expr.type.fields[field]:
            raise Exception('Field expression expected field type to match')
        self.type = type
        self.expr = expr
        self.field = field


class Forall(Expr):
    """
    An array forall expression.
    """

    def __init__(self, type, expr, invariant: Callable[[Expr], Expr]):
        if not isinstance(type, Bool):
            raise Exception('forall expression expected bool return type')
        if not isinstance(expr.type, Array):
            raise Exception('forall expression expected array type')
        self.type = type
        self.array_expr = Expr.convert(expr)
        self.invariant = invariant

class Evaluator(NodeVisitor):
    """
    A class that evaluates an Eywa Expression and returns a boolean.
    """

    def __init__(self, assignment):
        self.assignment = assignment

    def visit_Var(self, node):
        return self.assignment[node.parameter_name]

    def visit_Const(self, node):
        return node.constant

    def visit_Not(self, node):
        return not self.visit(node.expr)

    def visit_Match(self, node):
        return re.ismatch(node.regex, self.visit(node.expr))

    def visit_Field(self, node):
        return self.visit(node.expr)[node.field]

    def visit_Forall(self, node):
        old = self.assignment
        array = self.visit(node.array_expr)
        for element in array:
            var = Var(Type.inner(node.array_expr.type.element_type), uuid.uuid4())
            self.assignment = old.copy()
            self.assignment[var.parameter_name] = element
            expr = node.invariant(var)
            if not self.visit(expr):
                return False
        self.assignment = old
        return True

    def visit_Binop(self, node):
        e1 = self.visit(node.left)
        e2 = self.visit(node.right)
        if node.op == '==':
            return e1 == e2
        elif node.op == '!=':
            return e1 != e2
        elif node.op == '>':
            return e1 > e2
        elif node.op == '<':
            return e1 < e2
        elif node.op == '>=':
            return e1 >= e2
        elif node.op == '<=':
            return e1 <= e2
        elif node.op == '+':
            return e1 + e2
        elif node.op == '-':
            return e1 - e2
        elif node.op == '&':
            return e1 and e2
        elif node.op == '|':
            return e1 or e2
        raise Exception(f'Unknown binary operator: {node.op}')


class HasMatch(NodeVisitor):
    """
    A class that checks if an Eywa Expression has a match expression.
    """

    def visit_Var(self, node): return False
    def visit_Const(self, node): return False
    def visit_Match(self, node): return True
    def visit_Not(self, node): return self.visit(node.expr)
    def visit_Field(self, node): return self.visit(node.expr)

    def visit_Binop(self, node): return self.visit(
        node.left) or self.visit(node.right)
    def visit_Forall(self, node): return self.visit(node.array_expr) or self.visit(
        node.invariant(Var(Type.inner(node.array_expr.type.element_type), uuid.uuid4())))


class Parameter:
    """
    An Eywa parameter to a function.
    """

    def __init__(self, name: str, type: Type, description: Union[str, None] = None):
        self.name = name
        self.type = type
        self.description = description

    def __add__(self, other):
        """
        Override the + operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '+', Expr.convert(self), Expr.convert(other))

    def __sub__(self, other):
        """
        Override the - operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '-', Expr.convert(self), Expr.convert(other))

    def __and__(self, other):
        """
        Override the & operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '&', Expr.convert(self), Expr.convert(other))

    def __or__(self, other):
        """
        Override the | operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '|', Expr.convert(self), Expr.convert(other))

    def __le__(self, other):
        """
        Override the <= operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '<=', Expr.convert(self), Expr.convert(other))

    def __lt__(self, other):
        """
        Override the < operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '<', Expr.convert(self), Expr.convert(other))

    def __ge__(self, other):
        """
        Override the >= operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '>=', Expr.convert(self), Expr.convert(other))

    def __gt__(self, other):
        """
        Override the > operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '>', Expr.convert(self), Expr.convert(other))

    def __eq__(self, other):
        """
        Override the == operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '==', Expr.convert(self), Expr.convert(other))

    def __ne__(self, other):
        """
        Override the != operator to create a binary operation expression.
        """
        return Binop(Type.inner(self.type), '!=', Expr.convert(self), Expr.convert(other))

    def __invert__(self):
        """
        Override the bool operator to create a unary negation expression.
        """
        return Not(Bool(), Expr.convert(self))

    def matches(self, regex: re.Regex) -> Expr:
        """
        A helper function to create a match constraint.
        """
        return Match(Bool(), Expr.convert(self), regex)

    def get_field(self, field: str) -> Expr:
        """
        A helper function to create a field dereference.
        """
        return Field(Type.inner(self.type.fields[field]), Expr.convert(self), field)

    def forall(self, invariant: Callable[[Expr], Expr]) -> Expr:
        """
        A helper function to create an array forall expression.
        """
        return Forall(Bool(), Expr.convert(self), invariant)

    def implies(self, other) -> Expr:
        """
        A helper function to create an implies expression.
        """
        return Binop(Type.inner(self.type), '|', Not(Bool(), Expr.convert(self)), Expr.convert(other))


class Function:
    """
    An Eywa function that represents a model.
    """

    def __init__(self, name: str, description: str, inputs: List[Parameter], precondition: Union[Expr, None] = None):
        unique_names = set(map(lambda x: x.name, inputs))
        if len(unique_names) != len(inputs):
            raise Exception('duplicate parameter names')
        self.name = name
        self.description = description
        self.inputs = inputs[:-1]
        self.result = inputs[-1]
        self.precondition = precondition
        
class FuncModule(Function):
    """
    An Eywa function module used for composition
    """
    def __init__(self, name: str, description: str, inputs: List[Parameter]):
        unique_names = set(map(lambda x: x.name, inputs))
        
        if len(unique_names) != len(inputs):
            raise Exception('duplicate parameter names')
        self.name = name
        self.description = description
        self.inputs = inputs[:-1]
        self.result = inputs[-1]
        
        

        # print("Converted c_expr:", c_expr)
        
        
        

# class FunctionPrototype:
#     """
#     An Eywa function primitive used for composition
#     """
    
#     def __init__(self, name: str, description: str, inputs: List[Parameter]):
#         unique_names = set(map(lambda x: x.name, inputs))
        
#         if len(unique_names) != len(inputs):
#             raise Exception('duplicate parameter names')
#         self.name = name
#         self.description = description
#         self.inputs = inputs[:-1]
#         self.result = inputs[-1]
        