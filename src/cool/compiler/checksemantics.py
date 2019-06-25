from cool.utils import visitor
from cool.structs.environment import *
import cool.structs.cool_ast_hierarchy as cool
from cool.utils.config import *


class CheckSemanticsVisitor:
    def __init__(self):
        self.errors = []
        self.environment: Environment = Environment(self.errors)

    @visitor.on("node")
    def visit(self, node):
        pass

    @visitor.when(cool.ProgramNode)
    def visit(self, node: cool.ProgramNode):
        ok = False
        if self.environment.build_env(node):
            ok = True
            for cl in node.class_list:
                ok &= self.visit(cl)
        return ok

    @visitor.when(cool.ClassNode)
    def visit(self, node: cool.ClassNode):
        self.environment.enter_in_class(node.class_name)
        self.environment.create_child_scope()
        self.environment.define_variable("self", SELF_TYPE)

        ok = True

        if not self.environment.is_class_defined(node.ancestor):
            self.errors.append(Error(
                node.row, node.column, TYPE_ERROR, f"Class {node.ancestor} is not defined."))
            ok = False

        for attr in node.attrs_list:
            ok &= self.visit(attr)

        for meth in node.methods_list:
            ok &= self.visit(meth)

        self.environment.checkout_parent_scope()
        return ok

    @visitor.when(cool.AttributeDeclarationNode)
    def visit(self, node: cool.AttributeDeclarationNode):
        ok1 = True
        if node.attr_type != SELF_TYPE and not self.environment.is_class_defined(node.attr_type):
            self.errors.append(Error(
                node.row, node.column, TYPE_ERROR, f"Type {node.attr_type} is not defined."))
            ok1 = False

        ok2 = True
        if node.init_expr:
            expr_type, ok2 = self.visit(node.init_expr)

        ok = ok1 and ok2
        if ok and node.init_expr and not self.environment.conforms_to(expr_type, node.attr_type):
            self.errors.append(Error(node.row, node.column, TYPE_ERROR,
                                     f"Init expresion type ({expr_type}) does not conform to attribute declared type ({node.attr_type})."))
            ok = False
        return ok

    @visitor.when(cool.MethodDefinitionNode)
    def visit(self, node: cool.MethodDefinitionNode):
        self.environment.create_child_scope()
        self.environment.define_variable("self", SELF_TYPE)

        ok = True
        node.signature_vinfos = []
        for name, type in node.signature:
            if self.environment.is_local(name):
                self.errors.append(Error(node.row, node.column,  SEMANTIC_ERROR,
                                         f"Duplicate argument '{name}' in method definition."))
                ok = False
                break
            if type == SELF_TYPE:
                self.errors.append(
                    Error(node.row, node.column,  SEMANTIC_ERROR, f"Invalid usage of 'SELF_TYPE'."))
                ok = False
            else:
                node.signature_vinfos.append(
                    self.environment.define_variable(name, type))

        if ok:
            expr_type, ok = self.visit(node.body_expr)

            if ok and not self.environment.conforms_to(expr_type, node.return_type):
                self.errors.append(Error(node.row, node.column, TYPE_ERROR,
                                         f"Body expression type ({expr_type}) does not conform to method return type ({node.return_type})."))
                ok = False

        self.environment.checkout_parent_scope()
        return ok

    @visitor.when(cool.ArithmeticExpressionNode)
    def visit(self, node: cool.ArithmeticExpressionNode):
        left_type, ok1 = self.visit(node.left_expr)
        right_type, ok2 = self.visit(node.right_expr)
        ok = ok1 and ok2

        if ok and (not left_type == INT or not right_type == INT):
            self.errors.append(Error(node.row, node.column, TYPE_ERROR,
                                     f"Undefined operation between type {left_type} and type {right_type}."))
            ok = False

        node.type = INT
        return node.type, ok

    @visitor.when(cool.CompareExpressionNode)
    def visit(self, node: cool.CompareExpressionNode):
        left_type, ok1 = self.visit(node.left_expr)
        right_type, ok2 = self.visit(node.right_expr)
        ok = ok1 and ok2

        if ok and not left_type == INT or not right_type == INT:
            self.errors.append(Error(node.row, node.column,  TYPE_ERROR,
                                     f"Undefined operation between type {left_type} and type {right_type}."))
            ok = False

        node.type = BOOL
        return node.type, ok

    @visitor.when(cool.EqualNode)
    def visit(self, node: cool.EqualNode):
        left_type, ok1 = self.visit(node.left_expr)
        right_type, ok2 = self.visit(node.right_expr)
        ok = ok1 and ok2

        if left_type in [INT, BOOL, STRING] and not left_type == right_type:
            self.errors.append(Error(node.row, node.column,  TYPE_ERROR,
                                     f"Undefined operation between type {left_type} and type {right_type}."))
            ok = False

        node.type = BOOL
        return node.type, ok

    @visitor.when(cool.ArithNegationNode)
    def visit(self, node: cool.ArithNegationNode):
        expr_type, ok = self.visit(node.expr)

        if ok and not expr_type == INT:
            self.errors.append(Error(
                node.row, node.column,  TYPE_ERROR, f"Undefined operation on type  {expr_type}."))

        node.type = INT
        return node.type, ok

    @visitor.when(cool.BooleanNegationNode)
    def visit(self, node: cool.ArithNegationNode):
        expr_type, ok = self.visit(node.expr)

        if ok and not expr_type == BOOL:
            self.errors.append(Error(
                node.row, node.column, TYPE_ERROR, f"Undefined operation on type  {expr_type}."))

        node.type = BOOL
        return node.type, ok

    @visitor.when(cool.VariableNode)
    def visit(self, node: cool.VariableNode):
        ok = True
        if not self.environment.is_variable_defined(node.var_name):
            if not self.environment.is_attr_defined(node.var_name):
                self.errors.append(Error(node.row, node.column,  NAME_ERROR,
                                         f"Undefined name {node.var_name} in current scope."))
                ok = False
            else:
                node.variable_info = self.environment.get_attr_info(
                    node.var_name)
        else:
            node.variable_info = self.environment.get_variable_info(
                node.var_name)

        node.type = node.variable_info.type_name if ok else None
        return node.type, ok

    @visitor.when(cool.AssignNode)
    def visit(self, node: cool.AssignNode):
        ok1 = True
        if node.var_name == "self":
            self.errors.append(
                Error(node.row, node.column,  SEMANTIC_ERROR, f"Cannot assign variable self."))
            ok1 = False

        if ok1 and not self.environment.is_variable_defined(node.var_name):
            if not self.environment.is_attr_defined(node.var_name):
                self.errors.append(Error(node.row, node.column,  NAME_ERROR,
                                         f"Undefined variable {node.var_name} in current scope."))
                ok1 = False
            else:
                node.variable_info = self.environment.get_attr_info(
                    node.var_name)
        else:
            node.variable_info = self.environment.get_variable_info(
                node.var_name)

        expr_type, ok2 = self.visit(node.expr)
        ok = ok1 and ok2

        if ok and not self.environment.conforms_to(expr_type, node.variable_info.type_name):
            self.errors.append(Error(node.row, node.column,  TYPE_ERROR,
                                     f"Expression type ({expr_type}) does not conform to variable/attribute declared type ({node.variable_info.type_name})."))
            ok = False

        node.type = expr_type
        return node.type, ok

    @visitor.when(cool.BooleanNode)
    def visit(self, node: cool.BooleanNode):
        node.type = BOOL
        return BOOL, True

    @visitor.when(cool.IntegerNode)
    def visit(self, node: cool.IntegerNode):
        node.type = INT
        return INT, True

    @visitor.when(cool.StringNode)
    def visit(self, node: cool.StringNode):
        node.type = STRING
        return STRING, True

    @visitor.when(cool.NewNode)
    def visit(self, node: cool.NewNode):
        ok = True
        if node.type_name != SELF_TYPE and not self.environment.is_class_defined(node.type_name):
            self.errors.append(Error(
                node.row, node.column, TYPE_ERROR, f"Type {node.type_name} is not defined."))
            ok = False
        node.type = node.type_name
        return node.type, ok

    @visitor.when(cool.DynamicDispatchNode)
    def visit(self, node: cool.DynamicDispatchNode):
        dispatch_expr_type, ok1 = self.visit(node.dispatch_expr)
        dispatch_expr_type_prime = dispatch_expr_type if dispatch_expr_type != SELF_TYPE else self.environment.current_class_name

        ok2 = True
        if ok1 and not self.environment.is_method_defined(node.method_name, dispatch_expr_type_prime):
            self.errors.append(Error(node.row, node.column,  ATTRIBUTE_ERROR,
                                     f"Method {node.method_name} not defined in class {dispatch_expr_type_prime}."))
            ok2 = False

        params = [self.visit(param) for param in node.parameters]

        ok3 = all([ok for _, ok in params])

        params_types = [param_type for param_type, _ in params]
        ok4 = True
        if ok1 and ok2 and ok3:
            method_info = self.environment.get_method_info(
                node.method_name, dispatch_expr_type_prime)
            for param_type, arg_type in zip(params_types, method_info.signature):
                if not self.environment.conforms_to(param_type, arg_type):
                    self.errors.append(Error(node.row, node.column,  TYPE_ERROR,
                                             f"Parameter type {param_type} does not conform to argument type {arg_type}"))
                    ok4 = False

        ok = ok1 and ok2 and ok3 and ok4

        node.type = (
            dispatch_expr_type if method_info.signature[-1] == SELF_TYPE else method_info.signature[-1]) if ok else None
        return node.type, ok

    @visitor.when(cool.StaticDispatchNode)
    def visit(self, node: cool.StaticDispatchNode):
        dispatch_expr_type, ok1 = self.visit(node.dispatch_expr)
        dispatch_expr_type_prime = dispatch_expr_type if dispatch_expr_type != SELF_TYPE else self.environment.current_class_name

        ok5 = True
        if not self.environment.conforms_to(dispatch_expr_type, node.class_name):
            errors.append(Error(node.row, node.column, TYPE_ERROR,
                                f"Type {node.class_name} does not conform to type {dispatch_expr_type}"))

        ok2 = True
        if ok1 and not self.environment.is_method_defined(node.method_name, node.class_name):
            errors.append(Error(node.row, node.column, ATTRIBUTE_ERROR,
                                f"Method {node.method_name} not defined in class {node.class_name}."))
            ok2 = False

        params = [self.visit(param) for param in node.parameters]

        ok3 = all([ok for _, ok in params])

        params_types = [param_type for param_type, _ in params]
        ok4 = True
        if ok1 and ok2 and ok3:
            method_info = self.environment.get_method_info(
                node.method_name, dispatch_expr_type_prime)
            for param_type, arg_type in zip(params_types, method_info.signature):
                if not self.environment.conforms_to(param_type, arg_type):
                    self.errors.append(Error(node.row, node.column,  TYPE_ERROR,
                                             f"Parameter type {param_type} does not conform to argument type {arg_type}"))
                    ok4 = False

        ok = ok1 and ok2 and ok3 and ok4

        node.type = (
            dispatch_expr_type if method_info.signature[-1] == SELF_TYPE else method_info.signature[-1]) if ok else None
        return node.type, ok

    @visitor.when(cool.IfNode)
    def visit(self, node: cool.IfNode):
        cond_type, ok1 = self.visit(node.cond_expr)

        ok2 = True
        if not cond_type == BOOL:
            errors.append(Error(node.row, node.column, TYPE_ERROR,
                                f"Condition expression type must be Bool."))
            ok2 = False

        then_type, ok3 = self.visit(node.then_expr)
        else_type, ok4 = self.visit(node.else_expr)

        if ok3 and ok4:
            joint_type = self.environment.join_types([then_type, else_type])

        ok = ok1 and ok2 and ok3 and ok4

        node.type = joint_type if ok else None
        return node.type, ok

    @visitor.when(cool.BlockNode)
    def visit(self, node: cool.BlockNode):
        ok = True
        for expr in node.exprs_list:
            node.type, ok1 = self.visit(expr)
            ok &= ok1

        return node.type, ok

    @visitor.when(cool.LetNode)
    def visit(self, node: cool.LetNode):
        self.environment.create_child_scope()

        ok = True
        for declaration in node.declaration_list:
            ok &= self.visit(declaration)

        if ok:
            expr_type, ok = self.visit(node.expr)

        self.environment.checkout_parent_scope()

        node.type = expr_type if ok else None
        return node.type, ok

    @visitor.when(cool.LetDeclarationNode)
    def visit(self, node: cool.LetDeclarationNode):
        ok1 = True
        if node.var_name == "self":
            self.errors.append(Error(
                node.row, node.column,  SEMANTIC_ERROR, f"Invalid variable identifier self."))
            ok1 = False

        if ok1 and node.type_name != SELF_TYPE and not self.environment.is_class_defined(node.type_name):
            self.errors.append(Error(
                node.row, node.column, TYPE_ERROR, f"Type {node.type_name} is not defined."))
            ok1 = False

        ok2 = True
        if node.expr:
            expr_type, ok2 = self.visit(node.expr)

        ok = ok1 and ok2

        if ok and node.expr and not self.environment.conforms_to(expr_type, node.type_name):
            self.errors.append(Error(node.row, node.column, TYPE_ERROR,
                                     f"Init expresion type ({expr_type}) does not conform to variable declared type ({node.type_name})."))
            ok = False

        if self.environment.is_local(node.var_name):
            self.errors.append(Error(node.row, node.column,  SEMANTIC_ERROR,
                                     f"Variable '{node.var_name}' already declared in this scope."))
            ok = False
        else:
            node.variable_info = self.environment.define_variable(
                node.var_name, node.type_name)

        return ok

    @visitor.when(cool.WhileNode)
    def visit(self, node: cool.WhileNode):
        cond_type, ok1 = self.visit(node.cond_expr)

        ok2 = True
        if not cond_type == BOOL:
            self.errors.append(Error(
                node.row, node.column, TYPE_ERROR, f"Condition expression type must be Bool."))
            ok2 = False

        body_type, ok3 = self.visit(node.body_expr)

        ok = ok1 and ok2 and ok3

        node.type = OBJECT
        return node.type, ok

    @visitor.when(cool.IsVoidNode)
    def visit(self, node: cool.IsVoidNode):
        expr_type, ok = self.visit(node.expr)

        node.type = BOOL
        return node.type, ok

    @visitor.when(cool.CaseNode)
    def visit(self, node: cool.CaseNode):
        match_type, ok1 = self.visit(node.match_expr)

        ok2 = True
        declared_types = set()
        expr_types = []
        node.variable_info_list = []
        for var_name, type_name, case_expr in node.cases_list:
            if var_name == "self":
                self.errors.append(Error(
                    node.row, node.column,  SEMANTIC_ERROR, f"Invalid variable identifier self."))
                ok2 = False
            if type_name == SELF_TYPE:
                self.errors.append(
                    Error(node.row, node.column,  SEMANTIC_ERROR, f"Invalid usage of 'SELF_TYPE'."))
                ok2 = False
            if type_name in declared_types:
                self.errors.append(Error(
                    node.row, node.column,  SEMANTIC_ERROR, f"Repeated types in case branches."))
                ok2 = False
            declared_types.add(type_name)

            self.environment.create_child_scope()
            node.variable_info_list.append(
                self.environment.define_variable(var_name, type_name))

            expr_type, ok = self.visit(case_expr)
            expr_types.append(expr_type)
            ok2 &= ok
            self.environment.checkout_parent_scope()

        ok = ok1 and ok2

        node.type = self.environment.join_types(expr_types) if ok else None
        return node.type, ok
