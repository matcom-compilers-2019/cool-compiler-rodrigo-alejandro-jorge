import matplotlib.pyplot as plt
from cool.compiler.lexer import Lexer
import ply.yacc as yacc
import cool.structs.cool_ast_hierarchy as ast


def get_class_features(features):
    methods = [x for x in features if isinstance(x, ast.MethodDefinitionNode)]
    attrs = [x for x in features if isinstance(
        x, ast.AttributeDeclarationNode)]
    return attrs, methods


def assign_row_and_col(node, p, lines_starts, idx=1):
    node.row = p.lineno(idx)
    node.column =  p.lexpos(idx) - lines_starts[node.row]


class Parser(object):

    precedence = (
        ('right', 'ASSIGN'),
        ('right', 'NOT'),
        ('left', 'LTEQ', 'LT', 'EQ'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'MULTIPLY', 'DIVIDE'),
        ('right', 'ISVOID'),
        ('right', 'INT_COMP'),
        ('left', 'AT'),
        ('left', 'DOT')
    )

    def __init__(
            self,
            optimize=1,
            outputdir="",
            yacctab="cool.yacctab",
            write_tables=1,
            debug=1,
            build=True):
        self._optimize = optimize
        self._outputdir = outputdir
        self._yacctab = yacctab
        self._write_tables = write_tables
        self._debug = debug
        self.errors = []
        # get parser

        self.tokens = None
        self.lexer = None
        self.parser = None
        if build:
            self.build()

    def build(self):
        # get tokens
        self.lexer = Lexer()
        self.lexer.build()
        self.tokens = self.lexer.tokens
        self.parser = yacc.yacc(module=self)

    def __call__(self, program):
        return self.parser.parse(program)

############################################################################################################################################################
###################################################### GRAMMAR RULES #######################################################################################
############################################################################################################################################################

    def p_program(self, p):
        """
        program : class_list
        """
        p[0] = ast.ProgramNode(class_list=p[1])

    def p_class_list(self, p):
        """
        class_list : class_list class SEMICOLON
                   | class SEMICOLON
        """
        p[0] = [p[1]] if len(p) == 3 else p[1] + [p[2]]

    def p_class(self, p):
        """
        class : CLASS TYPE LBRACE features_list_optional RBRACE
        """
        attrs, methods = get_class_features(p[4])

        p[0] = ast.ClassNode(
            class_name=p[2],
            attrs_list=attrs,
            methods_list=methods,
            ancestor='Object'
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_class_with_inheritance(self, p):
        """
        class : CLASS TYPE INHERITS TYPE LBRACE features_list_optional RBRACE
        """
        attrs, methods = get_class_features(p[6])
        p[0] = ast.ClassNode(
            class_name=p[2],
            attrs_list=attrs,
            methods_list=methods,
            ancestor=p[4]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_features_list_optional(self, p):
        """
        features_list_optional : features_list
                               | empty
        """
        p[0] = p[1] if p[1] else []

    def p_features_list(self, p):
        """
        features_list : feature SEMICOLON
                      | feature SEMICOLON features_list
        """
        p[0] = [p[1]] if len(p) == 3 else [p[1]] + p[3]

    def p_feature_method(self, p):
        """
        feature : ID LPAREN formals_list RPAREN COLON TYPE LBRACE expression RBRACE
        """
        p[0] = ast.MethodDefinitionNode(
            method_name=p[1],
            signature=p[3],
            return_type=p[6],
            body_expr=p[8]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 1)

    def p_feature_method_no_formals(self, p):
        """
        feature : ID LPAREN RPAREN COLON TYPE LBRACE expression RBRACE
        """
        p[0] = ast.MethodDefinitionNode(
            method_name=p[1],
            signature=(),
            return_type=p[5],
            body_expr=p[7]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 1)

    def p_feature_attr_initialized(self, p):
        """
        feature : ID COLON TYPE ASSIGN expression
        """
        p[0] = ast.AttributeDeclarationNode(
            attr_name=p[1],
            attr_type=p[3],
            init_expr=p[5]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_feature_attr(self, p):
        """
        feature : ID COLON TYPE
        """
        p[0] = ast.AttributeDeclarationNode(
            attr_name=p[1],
            attr_type=p[3]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_formals_list(self, p):
        """
        formals_list : formals_list COMMA formal
                     | formal
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_formal(self, p):
        """
        formal : ID COLON TYPE
        """
        p[0] = (p[1], p[3])

    def p_expression_assignment(self, p):
        """
        expression : ID ASSIGN expression
        """
        p[0] = ast.AssignNode(var_name=p[1], expr=p[3])
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_expression_static_dispatch(self, p):
        """
        expression : expression AT TYPE DOT ID LPAREN arguments_list_opt RPAREN
        """
        p[0] = ast.StaticDispatchNode(
            dispatch_expr=p[1],
            class_name=p[3],
            method_name=p[5],
            parameters=p[7]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_expression_dispatch(self, p):
        """
        expression : expression DOT ID LPAREN arguments_list_opt RPAREN
        """
        p[0] = ast.DynamicDispatchNode(
            dispatch_expr=p[1],
            method_name=p[3],
            parameters=p[5]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_expression_dispatch_self_shortcut(self, p):
        """
        expression : ID LPAREN arguments_list_opt RPAREN
        """
        x = dispatch_expr = ast.VariableNode("self")
        assign_row_and_col(x, p, self.lexer.lines_starts)
        p[0] = ast.DynamicDispatchNode(
            x,
            method_name=p[1],
            parameters=p[3]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_arguments_list_opt(self, p):
        """
        arguments_list_opt : arguments_list
                           | empty
        """
        p[0] = p[1] if p[1] else []

    def p_arguments_list(self, p):
        """
        arguments_list : arguments_list COMMA expression
                       | expression
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_expression_if_conditional(self, p):
        """
        expression : IF expression THEN expression ELSE expression FI
        """
        p[0] = ast.IfNode(
            cond_expr=p[2],
            then_expr=p[4],
            else_expr=p[6]
        )

    def p_while_loop(self, p):
        """
        expression : WHILE expression LOOP expression POOL
        """
        p[0] = ast.WhileNode(
            cond_expr=p[2],
            body_expr=p[4]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 1)

    def p_expression_block(self, p):
        """
        expression : LBRACE block_list RBRACE
        """
        p[0] = ast.BlockNode(exprs_list=p[2])

    def p_block_list(self, p):
        """
        block_list : block_list expression SEMICOLON
                   | expression SEMICOLON
        """
        p[0] = [p[1]] if len(p) == 3 else p[1] + [p[2]]

    def p_expression_let(self, p):
        """
        expression : LET declarations_list IN expression
        """
        p[0] = ast.LetNode(
            declaration_list=p[2],
            expr=p[4]
        )

    def p_declarations_list(self, p):
        """
        declarations_list : declarations_list COMMA declaration
                          | declaration
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_declaration(self, p):
        """
        declaration : ID COLON TYPE ASSIGN expression
                    | ID COLON TYPE
        """
        expr = None if len(p) == 4 else p[5]
        p[0] = ast.LetDeclarationNode(
            var_name=p[1],
            type_name=p[3],
            expr=expr
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_expression_new(self, p):
        """
        expression : NEW TYPE
        """
        p[0] = ast.NewNode(type_name=p[2])
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_expression_isvoid(self, p):
        """
        expression : ISVOID expression
        """
        p[0] = ast.IsVoidNode(p[2])

    def p_expression_math_operations(self, p):
        """
        expression : expression PLUS expression
                   | expression MINUS expression
                   | expression MULTIPLY expression
                   | expression DIVIDE expression
        """
        if p[2] == '+':
            p[0] = ast.AdditionNode(left_expr=p[1], right_expr=p[3])
        elif p[2] == '-':
            p[0] = ast.SubstractionNode(left_expr=p[1], right_expr=p[3])
        elif p[2] == '*':
            p[0] = ast.MultiplicationNode(left_expr=p[1], right_expr=p[3])
        else:
            p[0] = ast.DivisionNode(left_expr=p[1], right_expr=p[3])
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_expression_integer_complement(self, p):
        """
        expression : INT_COMP expression
        """
        p[0] = ast.ArithNegationNode(p[2])
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 1)

    def p_expression_math_comparisons(self, p):
        """
        expression : expression LT expression
                     | expression LTEQ expression
                     | expression EQ expression
        """
        if p[2] == '<':
            p[0] = ast.LessNode(left_expr=p[1], right_expr=p[3])
        elif p[2] == '<=':
            p[0] = ast.LessEqNode(left_expr=p[1], right_expr=p[3])
        else:
            p[0] = ast.EqualNode(left_expr=p[1], right_expr=p[3])
        assign_row_and_col(p[0], p, self.lexer.lines_starts, 2)

    def p_expression_boolean_complement(self, p):
        """
        expression : NOT expression
        """
        p[0] = ast.BooleanNegationNode(p[2])
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_expression_with_parenthesis(self, p):
        """
        expression : LPAREN expression RPAREN
        """
        p[0] = p[2]

    def p_expression_identifier(self, p):
        """
        expression : ID
        """
        p[0] = ast.VariableNode(p[1])
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_expression_integer(self, p):
        """
        expression : INTEGER
        """
        p[0] = ast.IntegerNode(value=p[1])

    def p_expression_string(self, p):
        """
        expression : STRING
        """
        p[0] = ast.StringNode(value=p[1])

    def p_expression_true(self, p):
        """
        expression : TRUE
        """
        p[0] = ast.BooleanNode(True)

    def p_expression_false(self, p):
        """
        expression : FALSE
        """
        p[0] = ast.BooleanNode(False)

    def p_empty(self, p):
        """
        empty :
        """
        p[0] = None

    def p_expression_case(self, p):
        """
        expression : CASE expression OF actions_list ESAC
        """
        p[0] = ast.CaseNode(
            match_expr=p[2],
            cases_list=p[4]
        )
        assign_row_and_col(p[0], p, self.lexer.lines_starts)

    def p_actions_list(self, p):
        """
        actions_list : actions_list action SEMICOLON
                     | action SEMICOLON
        """
        p[0] = [p[1]] if len(p) == 3 else p[1] + [p[2]]

    def p_action(self, p):
        """
        action : ID COLON TYPE ARROW expression
        """
        p[0] = (p[1], p[3], p[5])

    # TODO SHOW ERRORS CUQUIS
    def p_error(self, p):
        """
        Error rule for Syntax Errors handling and reporting.
        """
        if not p:
            print("Error! Unexpected end of input!")
        else:
            error = "Syntax error! Line: {}, position: {}, character: {}, type: {}".format(
                p.lineno, p.lexpos, p.value, p.type)
            print(error)
            self.errors.append(error)
            self.parser.errok()
