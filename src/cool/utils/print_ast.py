from cool.utils import visitor
from cool.structs.environment import *
import cool.structs.cool_ast_hierarchy as cool
from cool.utils.config import *

class PrintAstVisitor:
    @visitor.on("node")
    def visit(self, node, indent):
        pass

    @visitor.when(cool.ProgramNode)
    def visit(self, node: cool.ProgramNode, indent):
        print(f"{' '*indent}PROGRAM NODE")
        for cl in node.class_list:
            self.visit(cl, indent+4)

    @visitor.when(cool.ClassNode)
    def visit(self, node: cool.ClassNode, indent):
        print(f"{' '*indent}CLASS NODE: {node.class_name} inherits {node.ancestor}")
        for attr in node.attrs_list:
            self.visit(attr, indent+4)

        for meth in node.methods_list:
            self.visit(meth, indent+4)

    @visitor.when(cool.AttributeDeclarationNode)
    def visit(self, node:cool.AttributeDeclarationNode, indent):
        print(f"{' '*indent}ATTRIBUTE_DECLARATION NODE: {node.attr_name}({node.attr_type})")
        if node.init_expr:
            self.visit(node.init_expr, indent+4)

    @visitor.when(cool.MethodDefinitionNode)
    def visit(self, node: cool.MethodDefinitionNode, indent):
        print(f"{' '*indent}METHOD_DEFINITION NODE: {node.method_name}{node.signature} ret {node.return_type}")

        self.visit(node.body_expr, indent+4)

    @visitor.when(cool.AdditionNode)
    def visit(self, node: cool.ArithmeticExpressionNode, indent):
        print(f"{' '*indent}ADDITION NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.SubstractionNode)
    def visit(self, node: cool.SubstractionNode, indent):
        print(f"{' '*indent}SUBSTRACTION NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.MultiplicationNode)
    def visit(self, node: cool.MultiplicationNode, indent):
        print(f"{' '*indent}MULTIPLICATION NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.DivisionNode)
    def visit(self, node: cool.DivisionNode, indent):
        print(f"{' '*indent}DIVISION NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.LessEqNode)
    def visit(self, node: cool.LessEqNode, indent):
        print(f"{' '*indent}LESS_EQ NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.EqualNode)
    def visit(self, node: cool.EqualNode, indent):
        print(f"{' '*indent}EQUAL NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.LessNode)
    def visit(self, node: cool.LessNode, indent):
        print(f"{' '*indent}LESS NODE")
        self.visit(node.left_expr, indent+4)
        self.visit(node.right_expr, indent+4)

    @visitor.when(cool.ArithNegationNode)
    def visit(self, node: cool.ArithNegationNode, indent):
        print(f"{' '*indent}ARITH_NEGATION NODE")
        self.visit(node.expr, indent+4)

    @visitor.when(cool.BooleanNegationNode)
    def visit(self, node: cool.BooleanNegationNode, indent):
        print(f"{' '*indent}BOOLEAN_NEGATION NODE")
        self.visit(node.expr, indent+4)

    @visitor.when(cool.VariableNode)
    def visit(self, node: cool.VariableNode, indent):
        print(f"{' '*indent}VARIABLE NODE: {node.var_name}")

    @visitor.when(cool.AssignNode)
    def visit(self, node: cool.AssignNode, indent):
        print(f"{' '*indent}ASSIGN NODE: {node.var_name}")
        self.visit(node.expr, indent+4)

    @visitor.when(cool.BooleanNode)
    def visit(self, node: cool.BooleanNode, indent):
        print(f"{' '*indent}BOOLEAN NODE: {node.value}")

    @visitor.when(cool.IntegerNode)
    def visit(self, node: cool.IntegerNode, indent):
        print(f"{' '*indent}INTEGER NODE: {node.value}")

    @visitor.when(cool.StringNode)
    def visit(self, node: cool.StringNode, indent):
        print(f"{' '*indent}STRING NODE: {node.value}")

    @visitor.when(cool.NewNode)
    def visit(self, node: cool.NewNode, indent):
        print(f"{' '*indent}NEW NODE: new {node.type_name}")

    @visitor.when(cool.DynamicDispatchNode)
    def visit(self, node: cool.DynamicDispatchNode, indent):
        print(f"{' '*indent}DYNAMIC_DISPATCH NODE: {node.method_name}")
        print(f"{' '*(indent+4)}DISPATCH_EXPR:")

        self.visit(node.dispatch_expr, indent+8)

        print(f"{' '*(indent+4)}PARAMETERS:")

        args = [self.visit(param, indent+8) for param in node.parameters]

    @visitor.when(cool.StaticDispatchNode)
    def visit(self, node: cool.StaticDispatchNode, indent):
        print(f"{' '*indent}DYNAMIC_DISPATCH NODE: {node.method_name}@{node.class_name}")
        print(f"{' '*(indent+4)}DISPATCH_EXPR:")

        self.visit(node.dispatch_expr, indent+8)

        print(f"{' '*(indent+4)}PARAMETERS:")

        args = [self.visit(param, indent+8) for param in node.parameters]

    @visitor.when(cool.IfNode)
    def visit(self, node: cool.IfNode, indent):
        print(f"{' '*indent}IF NODE:")
        print(f"{' '*(indent+4)}COND:")
        self.visit(node.cond_expr, indent+8)

        print(f"{' '*(indent+4)}THEN:")
        self.visit(node.then_expr, indent+8)
        print(f"{' '*(indent+4)}ELSE:")
        self.visit(node.else_expr, indent+8)

    @visitor.when(cool.BlockNode)
    def visit(self, node: cool.BlockNode, indent):
        print(f"{' '*indent}BLOCK NODE:")
        for expr in node.exprs_list:
            self.visit(expr, indent+4)

    @visitor.when(cool.LetNode)
    def visit(self, node: cool.LetNode, indent):
        print(f"{' '*indent}LET NODE:")
        print(f"{' '*(indent+4)}LET DECLARATION LIST:")
        for declaration in node.declaration_list:
            self.visit(declaration, indent+8)

        print(f"{' '*(indent+4)}LET EXPRESSION:")
        self.visit(node.expr, indent+8)

    @visitor.when(cool.LetDeclarationNode)
    def visit(self, node: cool.LetDeclarationNode, indent):
        print(f"{' '*indent}LET_DECLARATION NODE: {node.var_name}")
        if node.expr:
            self.visit(node.expr, indent+4)

    @visitor.when(cool.WhileNode)
    def visit(self, node: cool.WhileNode, indent):
        print(f"{' '*indent}WHILE NODE:")
        print(f"{' '*(indent+4)}COND:")
        self.visit(node.cond_expr, indent+8)

        print(f"{' '*(indent+4)}BODY:")
        self.visit(node.body_expr, indent+8)

    @visitor.when(cool.IsVoidNode)
    def visit(self, node: cool.IsVoidNode, indent):
        print(f"{' '*indent}ISVOID NODE:")
        self.visit(node.expr, indent+4)

    @visitor.when(cool.CaseNode)
    def visit(self, node: cool.CaseNode, indent):
        print(f"{' '*indent}CASE NODE:")
        self.visit(node.match_expr, indent+4)

        print(f"{' '*(indent+4)}CASES LIST:")
        for var_name, type_name, case_expr in node.cases_list:
            self.visit(case_expr, indent+8)