import cool.structs.cool_ast_hierarchy as cool
import cool.structs.cil_ast_hierarchy as cil
from cool.utils import visitor
from cool.structs.environment import VariableInfo, MethodInfo, ClassInfo
from cool.utils.config import *
from functools import *

class Label:
    def __init__(self, name):
        self.label_name = name

class COOLToCILVisitor:
    def __init__(self, environment):
        self.environment = environment

        self.dotdata = []
        self.dotcode = []

        self.current_class = None
        self.current_function = None

        self.localvars = []
        self.local_pointer = 0
        self.arguments = []
        self.instructions = []
        self.internal_count = 0
        self.label_count = 0

        self.cil_type_nodes = {}

        self.self_vinfo = VariableInfo("self")


    # ======================================================================
    # =[ UTILS ]============================================================
    # ======================================================================
    def get_closest_type(self, t_vinfo, case_types):
        loop_label = self.register_label("loop")
        pool_label = self.register_label("pool")

        self.register_instruction(cil.CILLabelNode, loop_label)
        eq = self.define_internal_local()
        for case_vinfo in case_types:
            self.register_instruction(cil.CILEqNode, eq, t_vinfo, case_vinfo)
            self.register_instruction(cil.CILGotoIfNode, eq, pool_label)

        self.register_instruction(cil.CILParentOfNode, t_vinfo, t_vinfo)
        #cuando no tiene padre que apunte a el mismo
        self.register_instruction(cil.CILEqNode, eq, t_vinfo, t_vinfo)
        self.register_instruction(cil.CILGotoIfNode, eq, pool_label)

        self.register_instruction(cil.CILGotoNode, loop_label)
        self.register_instruction(cil.CILLabelNode, pool_label)

        return t_vinfo

    def append_or_replace(self, methods, minfo):
        orig_names = [m.original_name for m in methods]
        if minfo.original_name in orig_names:
            idx = orig_names.index(minfo.original_name)
            methods[idx] = minfo
        else:
            methods.append(minfo)

    def topological_sort_classes(self, program_node):#just a BFS down types hierarchy
        n_class_list = []
        classes_dict = {class_node.class_name:class_node for class_node in program_node.class_list}
        predef_types_siblings = self.environment.types[OBJECT].siblings + self.environment.types[IO].siblings
        q = [classes_dict[cinfo.class_name].class_name for cinfo in predef_types_siblings if cinfo.class_name not in [IO,STRING,INT,BOOL]]
        while q:
            class_node = classes_dict[q.pop(0)]
            n_class_list.append(class_node)
            for child in self.environment.types[class_node.class_name].siblings:
                q.append(child.class_name)
        program_node.class_list = n_class_list

    def get_constructor_ast(self,class_node):
        expr_list = []
        #asignando primero los valores por defecto
        for attr in class_node.attrs_list:
            assign = cool.AssignNode(attr.attr_name, cool.DefaultValueNode(attr.variable_info.type_name))
            assign.variable_info = attr.variable_info
            expr_list.append(assign)
        #despues, si hay expresion de inicializacion se les pone
        for attr in class_node.attrs_list:
            if attr.init_expr:
                assign = cool.AssignNode(attr.attr_name, attr.init_expr)
                assign.variable_info = attr.variable_info
                expr_list.append(assign)
        body_expr = cool.BlockNode(expr_list)

        constructor_minfo = MethodInfo("constructor", [])
        current_class = self.environment.types[class_node.class_name]
        current_class.constructor = constructor_minfo
        current_class.methods[constructor_minfo.method_name] = constructor_minfo

        return cool.MethodDefinitionNode(constructor_minfo.method_name, [], OBJECT, body_expr)

    def append_constructors(self, program_node):
        for class_node in program_node.class_list:
            class_node.methods_list.append(self.get_constructor_ast(class_node))

    def build_internal_vname(self, vname):
        vname = f"{self.internal_count}_{self.current_function.original_name}_{vname}"
        self.internal_count += 1
        return vname

    def build_internal_mname(self, mname):
        mname = f"{self.current_class.class_name}_{mname}"
        return mname

    def define_internal_local(self):
        if self.local_pointer == len(self.localvars):
            vinfo = VariableInfo('internal')
            self.register_local(vinfo)
        else:
            self.local_pointer += 1
        return self.localvars[self.local_pointer-1].vinfo

    def register_local(self, vinfo, arg = False):
        vinfo.var_name = self.build_internal_vname(vinfo.var_name)
        local_node = cil.CILLocalNode(vinfo)
        self.localvars.insert(self.local_pointer, local_node)
        self.local_pointer += 1
        return vinfo

    def register_argument(self, vinfo):
        vinfo.var_name = self.build_internal_vname(vinfo.var_name)
        arg_node = cil.CILArgNode(vinfo)
        self.arguments.append(arg_node)
        return vinfo

    def register_label(self, lname):
        lname = f"{lname}_{self.label_count}"
        self.label_count += 1
        return Label(lname)

    def register_instruction(self, instruction_type, *args):
        instruction = instruction_type(*args)
        self.instructions.append(instruction)
        return instruction

    def register_data(self, value):
        strs = [data_node.value for data_node in self.dotdata]
        if value in strs:
            data_node = self.dotdata[strs.index(value)]
        else:
            vname = f'data_{len(self.dotdata)}'
            data_node = cil.CILDataNode(vname, value)
            self.dotdata.append(data_node)
        return data_node

    def predefined_types(self):
        #Object
        obj_functions = [
            self.cil_predef_method("abort", OBJECT, self.object_abort),
            self.cil_predef_method("copy", OBJECT, self.object_copy),
            self.cil_predef_method("type_name", OBJECT, self.object_type_name)
        ]
        object_type = cil.CILTypeNode(self.environment.types[OBJECT], [], obj_functions)

        #IO
        functions = [
            self.cil_predef_method("out_string", IO, self.io_outstring),
            self.cil_predef_method("out_int", IO, self.io_outint),
            self.cil_predef_method("in_string", IO, self.io_instring),
            self.cil_predef_method("in_int", IO, self.io_inint)
        ]
        io_type = cil.CILTypeNode(self.environment.types[IO], [], obj_functions + functions)

        #String
        functions = [
            self.cil_predef_method("length", STRING, self.string_length),
            self.cil_predef_method("concat", STRING, self.string_concat),
            self.cil_predef_method("substr", STRING, self.string_substr)
        ]
        string_type = cil.CILTypeNode(self.environment.types[STRING], [VariableInfo("length"), VariableInfo("str_ref")], obj_functions + functions)

        #Int
        int_type = cil.CILTypeNode(self.environment.types[INT], [VariableInfo("value", is_attr=True)], obj_functions)

        #Bool
        bool_type = cil.CILTypeNode(self.environment.types[BOOL], [VariableInfo("value", is_attr=True)], obj_functions)

        self.cil_type_nodes[OBJECT] = object_type
        self.cil_type_nodes[IO] = io_type
        self.cil_type_nodes[STRING] = string_type
        self.cil_type_nodes[INT] = int_type
        self.cil_type_nodes[BOOL] = bool_type
        return [object_type, io_type, string_type, int_type, bool_type]

    def is_boxing_scenario(self, dest, orig):
        return dest == OBJECT and orig in [INT,BOOL]

    def get_default_value(self, class_name):
        return DefaultValue(class_name)

    #predefined functions cil
    def cil_predef_method(self, mname, cname, specif_code):
        self.internal_count = 0
        self.localvars = []
        self.local_pointer = 0
        self.arguments = []
        self.instructions = []

        self.current_class = self.environment.types[cname]

        function_minfo = self.environment.get_method_info(mname, cname)
        function_minfo.method_name = self.build_internal_mname(function_minfo.method_name)
        self.current_function = function_minfo

        specif_code()

        self.dotcode.append(cil.CILFunctionNode(function_minfo, self.arguments, self.localvars, self.instructions))
        return function_minfo

    def string_length(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))

        ret_vinfo = self.define_internal_local()

        self.register_instruction(cil.CILLengthNode, ret_vinfo, self.self_vinfo)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    def string_concat(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        other_arg = VariableInfo("other_arg")
        self.register_argument(other_arg)

        ret_vinfo = self.define_internal_local()

        self.register_instruction(cil.CILConcatNode, ret_vinfo, self.self_vinfo, other_arg)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    def string_substr(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        idx_arg = VariableInfo("idx_arg")
        self.register_argument(idx_arg)
        length_arg = VariableInfo("length_arg")
        self.register_argument(length_arg)

        ret_vinfo = self.define_internal_local()

        self.register_instruction(cil.CILSubstringNode, ret_vinfo, self.self_vinfo, idx_arg, length_arg)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    def object_abort(self):
        self.register_instruction(cil.CILRuntimeErrorNode, ABORT_SIGNAL)

    def object_copy(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        ret_vinfo = self.define_internal_local()
        self.register_instruction(cil.CILCopyNode, ret_vinfo, self.self_vinfo)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    def object_type_name(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        ret_vinfo = self.define_internal_local()
        self.register_instruction(cil.CILTypeNameNode, ret_vinfo, self.self_vinfo)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    def io_outstring(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        str_arg = VariableInfo("str")
        self.register_argument(str_arg)
        self.register_instruction(cil.CILPrintStringNode, str_arg)
        self.register_instruction(cil.CILReturnNode, self.self_vinfo)

    def io_outint(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        int_arg = VariableInfo("int")
        self.register_argument(int_arg)
        self.register_instruction(cil.CILPrintIntNode, int_arg)
        self.register_instruction(cil.CILReturnNode, self.self_vinfo)

    def io_instring(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        ret_vinfo = self.define_internal_local()
        self.register_instruction(cil.CILReadStringNode, ret_vinfo)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    def io_inint(self):
        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        ret_vinfo = self.define_internal_local()
        self.register_instruction(cil.CILReadIntNode, ret_vinfo)
        self.register_instruction(cil.CILReturnNode, ret_vinfo)

    # ======================================================================


    # ======================================================================
    # =[ VISIT ]============================================================
    # ======================================================================

    @visitor.on('node')
    def visit(self, node, ret_vinfo = None):
        pass

    @visitor.when(cool.ProgramNode)
    def visit(self, node, ret_vinfo = None):
        self.topological_sort_classes(node)

        dottypes = self.predefined_types()
        self.append_constructors(node)

        for class_node in node.class_list:
            dottypes.append(self.visit(class_node))

        return cil.CILProgramNode(dottypes, self.dotdata, self.dotcode)

    @visitor.when(cool.ClassNode)
    def visit(self, node, ret_vinfo = None):
        self.current_class = self.environment.types[node.class_name]

        attributes = self.cil_type_nodes[self.current_class.ancestor.class_name].attributes.copy()
        for attribute in node.attrs_list:
            attributes.append(self.visit(attribute))

        functions = self.cil_type_nodes[self.current_class.ancestor.class_name].functions.copy()

        for method in node.methods_list:
            minfo = self.visit(method)
            self.append_or_replace(functions, minfo)

        type_node = cil.CILTypeNode(self.current_class, attributes, functions)
        self.cil_type_nodes[self.current_class.class_name] = type_node

        return type_node

    @visitor.when(cool.AttributeDeclarationNode)
    def visit(self, node, ret_vinfo = None):
        return self.environment.get_attr_info(node.attr_name, self.current_class.class_name)

    @visitor.when(cool.MethodDefinitionNode)
    def visit(self, node, ret_vinfo = None):
        self.internal_count = 0
        self.localvars = []
        self.local_pointer = 0
        self.arguments = []
        self.instructions = []

        function_minfo = self.environment.get_method_info(node.method_name, self.current_class.class_name)
        function_minfo.method_name = self.build_internal_mname(function_minfo.method_name)
        self.current_function = function_minfo

        self.arguments.append(cil.CILArgNode(self.self_vinfo))
        for arg in node.signature_vinfos:
            self.register_argument(arg)

        ret_vinfo = self.define_internal_local()
        self.visit(node.body_expr, ret_vinfo)

        self.register_instruction(cil.CILReturnNode, ret_vinfo)
        self.dotcode.append(cil.CILFunctionNode(function_minfo, self.arguments, self.localvars, self.instructions))

        return function_minfo

    @visitor.when(cool.AdditionNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)

        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        self.register_instruction(cil.CILPlusNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.SubstractionNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)

        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        self.register_instruction(cil.CILMinusNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.MultiplicationNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)


        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        self.register_instruction(cil.CILStarNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.DivisionNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)

        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        self.register_instruction(cil.CILDivNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.ArithNegationNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        right_vinfo = self.define_internal_local()
        self.visit(node.expr, right_vinfo)
        self.register_instruction(cil.CILMinusNode, ret_vinfo, 0, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.EqualNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)

        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        if node.left_expr.type == STRING:
            self.register_instruction(cil.CILStrEqNode, ret_vinfo, left_vinfo, right_vinfo)
        else:
            self.register_instruction(cil.CILEqNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.LessEqNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)

        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        self.register_instruction(cil.CILLessEqNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.LessNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        left_vinfo = self.define_internal_local()
        self.visit(node.left_expr, left_vinfo)

        right_vinfo = self.define_internal_local()
        self.visit(node.right_expr, right_vinfo)

        self.register_instruction(cil.CILLessNode, ret_vinfo, left_vinfo, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.BooleanNegationNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        expr_vinfo = self.define_internal_local()
        self.visit(node.expr, expr_vinfo)
        self.register_instruction(cil.CILMinusNode, ret_vinfo, 1, expr_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.LetNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        for decl in node.declaration_list:
            self.register_local(decl.variable_info)
            self.visit(decl)

        self.visit(node.expr, ret_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.LetDeclarationNode)
    def visit(self, node, ret_vinfo = None):
        s_pointer = self.local_pointer

        initializer = cool.DefaultValueNode(node.type_name) if not node.expr else node.expr
        right_vinfo = self.define_internal_local()
        self.visit(initializer, right_vinfo)

        if node.expr and self.is_boxing_scenario(node.variable_info.type_name, node.expr.type):
            boxed_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILBoxNode, boxed_vinfo, right_vinfo, node.expr.type)
            right_vinfo = boxed_vinfo

        self.register_instruction(cil.CILAssignNode, node.variable_info, right_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.BlockNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        for expr in node.exprs_list:
            self.visit(expr, ret_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.AssignNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        self.visit(node.expr, ret_vinfo)

        if self.is_boxing_scenario(node.variable_info.type_name, node.expr.type):
            boxed_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILBoxNode, boxed_vinfo, ret_vinfo, node.expr.type)
            ret_vinfo = boxed_vinfo

        if node.variable_info.is_attr:
            self.register_instruction(cil.CILSetAttribNode, self.self_vinfo, node.variable_info, ret_vinfo)
        else:
            self.register_instruction(cil.CILAssignNode, node.variable_info, ret_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.VariableNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        if node.variable_info.is_attr:
            self.register_instruction(cil.CILGetAttribNode, ret_vinfo, self.self_vinfo, node.variable_info)
        else:
            if node.variable_info.var_name == "self":
                node.variable_info = self.self_vinfo
            self.register_instruction(cil.CILAssignNode, ret_vinfo, node.variable_info)

        self.local_pointer = s_pointer

    @visitor.when(cool.NewNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        c_vinfo = self.define_internal_local()

        if node.type_name in [INT, BOOL]:
            self.register_instruction(cil.CILDefaultValueNode, ret_vinfo, node.type_name)
        elif node.type_name != SELF_TYPE:
            type_cinfo = self.environment.types[node.type_name]
            self.register_instruction(cil.CILAllocateNode, ret_vinfo, type_cinfo)
            self.register_instruction(cil.CILParamNode, ret_vinfo)
            if node.type_name not in [IO, OBJECT]:
                self.register_instruction(cil.CILStaticCallNode, c_vinfo, type_cinfo.constructor)
        else:
            self.register_instruction(cil.CILAllocateSelfNode, ret_vinfo)
            self.register_instruction(cil.CILParamNode, ret_vinfo)
            self.register_instruction(cil.CILDinamicCallNode, c_vinfo, self.self_vinfo, self.current_class.constructor)

        self.local_pointer = s_pointer

    @visitor.when(cool.IfNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        then_label = self.register_label("then_label")
        fi_label = self.register_label("fi_label")

        cond_vinfo = self.define_internal_local()
        self.visit(node.cond_expr, cond_vinfo)
        self.register_instruction(cil.CILGotoIfNode, cond_vinfo, then_label)

        else_vinfo = self.define_internal_local()
        self.visit(node.else_expr, else_vinfo)
        self.register_instruction(cil.CILAssignNode, ret_vinfo, else_vinfo)
        self.register_instruction(cil.CILGotoNode, fi_label)

        self.register_instruction(cil.CILLabelNode, then_label)

        then_vinfo = self.define_internal_local()
        self.visit(node.then_expr, then_vinfo)
        self.register_instruction(cil.CILAssignNode, ret_vinfo, then_vinfo)

        self.register_instruction(cil.CILLabelNode, fi_label)

        self.local_pointer = s_pointer

    @visitor.when(cool.WhileNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        loop_label = self.register_label("loop")
        pool_label = self.register_label("pool")
        body_label = self.register_label("body")

        self.register_instruction(cil.CILLabelNode, loop_label)

        cond_vinfo = self.define_internal_local()
        self.visit(node.cond_expr, cond_vinfo)

        self.register_instruction(cil.CILGotoIfNode, cond_vinfo, body_label)
        self.register_instruction(cil.CILGotoNode, pool_label)

        self.register_instruction(cil.CILLabelNode, body_label)

        body_vinfo = self.define_internal_local()
        self.visit(node.body_expr, body_vinfo)

        self.register_instruction(cil.CILGotoNode, loop_label)

        self.register_instruction(cil.CILLabelNode, pool_label)
        self.register_instruction(cil.CILDefaultValueNode, ret_vinfo, OBJECT)

        self.local_pointer = s_pointer

    @visitor.when(cool.DynamicDispatchNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        expr_static_type = node.dispatch_expr.type if node.dispatch_expr.type != SELF_TYPE else self.current_class.class_name
        function_minfo = self.environment.get_method_info(node.method_name, expr_static_type)

        params = []
        for i,param_expr in enumerate(node.parameters):
            param_vinfo = self.define_internal_local()
            self.visit(param_expr, param_vinfo)
            if self.is_boxing_scenario(function_minfo.signature[i], param_expr.type):
                boxed_vinfo = self.define_internal_local()
                self.register_instruction(cil.CILBoxNode, boxed_vinfo, param_vinfo, param_expr.type)
                param_vinfo = boxed_vinfo
            params.append(param_vinfo)

        expr_vinfo = self.define_internal_local()
        self.visit(node.dispatch_expr, expr_vinfo)

        for param_vinfo in reversed(params):
            self.register_instruction(cil.CILParamNode, param_vinfo)

        if expr_static_type in [INT, BOOL]:
            boxed_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILBoxNode, boxed_vinfo, expr_vinfo, expr_static_type)
            expr_vinfo = boxed_vinfo
        self.register_instruction(cil.CILParamNode, expr_vinfo)

        if expr_static_type in [INT, BOOL]:
            self.register_instruction(cil.CILStaticCallNode, ret_vinfo, function_minfo)
            if node.method_name == 'copy':
                self.register_instruction(cil.CILUnboxNode, ret_vinfo)
        else:
            self.register_instruction(cil.CILDinamicCallNode, ret_vinfo, expr_vinfo, function_minfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.StaticDispatchNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        expr_static_type = node.dispatch_expr.type if node.dispatch_expr.type != SELF_TYPE else self.current_class.class_name
        function_minfo = self.environment.get_method_info(node.method_name, node.class_name)

        params = []
        for i,param_expr in enumerate(node.parameters):
            param_vinfo = self.define_internal_local()
            self.visit(param_expr, param_vinfo)
            if self.is_boxing_scenario(function_minfo.signature[i], param_expr.type):
                boxed_vinfo = self.define_internal_local()
                self.register_instruction(cil.CILBoxNode, boxed_vinfo, param_vinfo, param_expr.type)
                param_vinfo = boxed_vinfo
            params.append(param_vinfo)

        expr_vinfo = self.define_internal_local()
        self.visit(node.dispatch_expr, expr_vinfo)

        for param_vinfo in reversed(params):
            self.register_instruction(cil.CILParamNode, param_vinfo)

        if expr_static_type in [INT, BOOL]:
            boxed_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILBoxNode, boxed_vinfo, expr_vinfo, expr_static_type)
            expr_vinfo = boxed_vinfo

        self.register_instruction(cil.CILParamNode, expr_vinfo)

        self.register_instruction(cil.CILStaticCallNode, ret_vinfo, function_minfo)
        if node.method_name == 'copy' and expr_static_type in [INT, BOOL]:
            self.register_instruction(cil.CILUnboxNode, ret_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.IsVoidNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        if node.expr.type in [INT, BOOL, STRING]:
            self.register_instruction(cil.CILAssignNode, ret_vinfo, 0)
        else:
            expr_vinfo = self.define_internal_local()
            self.visit(node.expr, expr_vinfo)
            self.register_instruction(cil.CILIsVoidNode, ret_vinfo, expr_vinfo)

        self.local_pointer = s_pointer

    @visitor.when(cool.CaseNode)
    def visit(self, node, ret_vinfo):
        s_pointer = self.local_pointer

        case_vinfo = self.define_internal_local()
        self.visit(node.match_expr, case_vinfo)

        #box always
        if node.match_expr.type in [INT, BOOL]:
            boxed_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILBoxNode, boxed_vinfo, case_vinfo, node.match_expr.type)
            case_vinfo = boxed_vinfo

        matchtype_cinfo = self.define_internal_local()
        self.register_instruction(cil.CILTypeOfNode, matchtype_cinfo, case_vinfo)

        classes_info_list = [self.environment.types[type] for _,type,_ in node.cases_list]
        expressions = [expr for _,_,expr in node.cases_list]
        zipped_info = zip(node.variable_info_list, classes_info_list, expressions)

        closest_cinfo = self.get_closest_type(matchtype_cinfo, classes_info_list)

        end_label = self.register_label(f"end")
        for i,(vinfo, cinfo, expr) in enumerate(zipped_info):
            self.register_local(vinfo)
            next_label = self.register_label(f"next{i}")

            eq_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILEqNode, eq_vinfo, closest_cinfo, cinfo)
            neq_vinfo = self.define_internal_local()
            self.register_instruction(cil.CILMinusNode, neq_vinfo, 1, eq_vinfo)

            self.register_instruction(cil.CILGotoIfNode, neq_vinfo, next_label)

            #unboxing if value type
            if node.match_expr.type in [INT, BOOL]:
                self.register_instruction(cil.CILUnboxNode, case_vinfo)
            self.register_instruction(cil.CILAssignNode, vinfo, case_vinfo)
            expr_vinfo = self.define_internal_local()
            self.visit(expr, expr_vinfo)
            self.register_instruction(cil.CILAssignNode, ret_vinfo, expr_vinfo)
            self.register_instruction(cil.CILGotoNode, end_label)

            self.register_instruction(cil.CILLabelNode, next_label)
        self.register_instruction(cil.CILRuntimeErrorNode, CASE_MISSMATCH)
        self.register_instruction(cil.CILLabelNode, end_label)

        self.local_pointer = s_pointer

    @visitor.when(cool.IntegerNode)
    def visit(self, node, ret_vinfo):
        self.register_instruction(cil.CILAssignNode, ret_vinfo, int(node.value))

    @visitor.when(cool.BooleanNode)
    def visit(self, node, ret_vinfo):
        self.register_instruction(cil.CILAssignNode, ret_vinfo, 1 if node.value else 0)

    @visitor.when(cool.StringNode)
    def visit(self, node, ret_vinfo):
        msg = self.register_data(node.value)
        self.register_instruction(cil.CILLoadNode, ret_vinfo, msg)

    @visitor.when(cool.DefaultValueNode)
    def visit(self, node, ret_vinfo):
        self.register_instruction(cil.CILDefaultValueNode, ret_vinfo, node.class_name)
    # ======================================================================