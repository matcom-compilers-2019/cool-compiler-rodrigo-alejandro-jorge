class Node:
    def __init__(self):
        self.row = -1
        self.column = -1

class UtilNode(Node):
    pass

class ProgramNode(Node):
    def __init__(self,class_list):
        self.class_list=class_list

class ClassNode(Node):
    def __init__(self,class_name, attrs_list, methods_list, ancestor="Object"):
        self.class_name=class_name
        self.attrs_list=attrs_list
        self.methods_list=methods_list
        self.ancestor=ancestor

class AttributeDeclarationNode(UtilNode):
    def __init__(self, attr_name, attr_type, init_expr=None):
        self.attr_name = attr_name
        self.attr_type = attr_type
        self.init_expr = init_expr

class MethodDefinitionNode(UtilNode):
    def __init__(self, method_name, signature, return_type, body_expr):
        self.method_name = method_name
        self.signature = signature
        self.return_type = return_type
        self.signature_vinfos = [None for _ in signature]
        self.body_expr = body_expr

class ExpressionNode(Node):
    def __init__(self):
        self.type = None

class BinaryExpressionNode(ExpressionNode):
    def __init__(self,left_expr,right_expr):
        ExpressionNode.__init__(self)
        self.left_expr=left_expr
        self.right_expr=right_expr

class UnaryExpressionNode(ExpressionNode):
    def __init__(self,expr):
        ExpressionNode.__init__(self)
        self.expr=expr

class AtomicNode(ExpressionNode):
    pass

class ArithmeticExpressionNode(BinaryExpressionNode):
    pass

class CompareExpressionNode(BinaryExpressionNode):
    pass

class AdditionNode(ArithmeticExpressionNode):
    pass

class SubstractionNode(ArithmeticExpressionNode):
    pass

class MultiplicationNode(ArithmeticExpressionNode):
    pass

class DivisionNode(ArithmeticExpressionNode):
    pass

class LessNode(CompareExpressionNode):
    pass

class LessEqNode(CompareExpressionNode):
    pass

class EqualNode(BinaryExpressionNode):
    pass

class ArithNegationNode(UnaryExpressionNode):
    pass

class BooleanNegationNode(UnaryExpressionNode):
    pass

class IsVoidNode(UnaryExpressionNode):
    pass

class ConstantNode(AtomicNode):
    pass

class IntegerNode(ConstantNode):
    def __init__(self, value):
        self.value=int(value)

class BooleanNode(ConstantNode):
    def __init__(self, value):
        self.value=bool(value)

class StringNode(ConstantNode):
    def __init__(self, value):
        self.value=value

class NewNode(AtomicNode):
    def __init__(self, type_name):
        self.type_name=type_name

class IfNode(AtomicNode):
    def __init__(self, cond_expr, then_expr, else_expr):
        self.cond_expr = cond_expr
        self.then_expr = then_expr
        self.else_expr = else_expr

class WhileNode(AtomicNode):
    def __init__(self,cond_expr,body_expr):
        self.cond_expr = cond_expr
        self.body_expr = body_expr

class CaseNode(AtomicNode):
    def __init__(self, match_expr, cases_list):#un case es una tupla (id,type,expr)
        self.match_expr = match_expr
        self.cases_list = cases_list
        self.variable_info_list = [None for _ in cases_list]

class DispatchNode(AtomicNode):
    def __init__(self, dispatch_expr,method_name, parameters):
        self.dispatch_expr = dispatch_expr
        self.method_name = method_name
        self.parameters = parameters

class DynamicDispatchNode(DispatchNode):
    pass

class StaticDispatchNode(DispatchNode):
    def __init__(self, dispatch_expr,method_name, parameters, class_name):
        DispatchNode.__init__(self, dispatch_expr, method_name, parameters)
        self.class_name = class_name

class BlockNode(AtomicNode):
    def __init__(self, exprs_list):
        self.exprs_list=exprs_list

class AssignNode(AtomicNode):
    def __init__(self, var_name, expr):
        self.var_name = var_name
        self.expr = expr
        self.variable_info = None

class VariableNode(AtomicNode):
    def __init__(self,var_name):
        self.var_name=var_name
        self.variable_info = None

class LetDeclarationNode(UtilNode):
    def __init__(self, var_name, type_name, expr=None):
        self.var_name = var_name
        self.type_name = type_name
        self.expr = expr
        self.variable_info = None

class LetNode(AtomicNode):
    def __init__(self, declaration_list, expr):
        self.declaration_list = declaration_list
        self.expr = expr

class DefaultValueNode(ConstantNode):
    def __init__(self, class_name):
        self.class_name = class_name
        self.type = "Object"