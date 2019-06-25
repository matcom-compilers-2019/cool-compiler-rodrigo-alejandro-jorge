import cool.structs.cil_ast_hierarchy as cil
from cool.utils import visitor
from cool.structs.environment import *

class CILWriterVisitor(object):
    def __init__(self):
        self.output = []

    def emit(self, msg):
        self.output.append(msg)

    def black(self):
        self.output.append('')

    def get_value(self, value):
        if (isinstance(value, int) or isinstance(value, str) or isinstance(value, bool)):
            return value
        elif (isinstance(value, VariableInfo)):
            return value.var_name
        elif (isinstance(value, ClassInfo)):
            return value.class_name

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(cil.CILProgramNode)
    def visit(self, node:cil.CILProgramNode):
        self.emit('.TYPES')
        for x in node.dottypes:
            self.visit(x)
        self.black()

        self.emit('.DATA')
        for x in node.dotdata:
            self.visit(x)
        self.black()

        self.emit('.CODE')
        for x in node.dotcode:
            self.visit(x)


    @visitor.when(cil.CILTypeNode)
    def visit(self, node:cil.CILTypeNode):
        self.emit(f"type {node.class_info.class_name} {{")
        for attr in node.attributes:
            self.emit(f"    attribute {attr.var_name};")

        for function in node.functions:
            self.emit(f"    method {function.original_name}: {function.method_name};")

        self.emit("}")

    @visitor.when(cil.CILDataNode)
    def visit(self, node:cil.CILDataNode):
        self.emit(f'{node.vname} = "{node.value}"')

    @visitor.when(cil.CILFunctionNode)
    def visit(self, node:cil.CILFunctionNode):
        self.black()

        self.emit(f'function {node.method_info.method_name} {{')
        for x in node.arguments:
            self.visit(x)
        if node.arguments:
            self.black()

        for x in node.localvars:
            self.visit(x)
        if node.localvars:
            self.black()

        for x in node.instructions:
            self.visit(x)
        self.emit('}')

    @visitor.when(cil.CILParamNode)
    def visit(self, node:cil.CILParamNode):
        self.emit(f"    PARAM {self.get_value(node.vinfo)};")

    @visitor.when(cil.CILLocalNode)
    def visit(self, node:cil.CILLocalNode):
        self.emit(f'    LOCAL {self.get_value(node.vinfo)};')

    @visitor.when(cil.CILAssignNode)
    def visit(self, node:cil.CILAssignNode):
        dest = node.dest.var_name
        source = self.get_value(node.source)
        self.emit(f'    {dest} = {source};')

    @visitor.when(cil.CILPlusNode)
    def visit(self, node:cil.CILPlusNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} + {right};')

    @visitor.when(cil.CILMinusNode)
    def visit(self, node:cil.CILMinusNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} - {right};')

    @visitor.when(cil.CILStarNode)
    def visit(self, node:cil.CILStarNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} * {right};')

    @visitor.when(cil.CILDivNode)
    def visit(self, node:cil.CILDivNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} / {right};')

    @visitor.when(cil.CILEqNode)
    def visit(self, node:cil.CILEqNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} == {right};')

    @visitor.when(cil.CILStrEqNode)
    def visit(self, node:cil.CILStrEqNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} =s= {right};')


    @visitor.when(cil.CILLessEqNode)
    def visit(self, node:cil.CILLessEqNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} <= {right};')

    @visitor.when(cil.CILLessNode)
    def visit(self, node:cil.CILLessNode):
        dest = node.dest.var_name
        left = self.get_value(node.left)
        right = self.get_value(node.right)
        self.emit(f'    {dest} = {left} < {right};')

    @visitor.when(cil.CILGetAttribNode)
    def visit(self, node:cil.CILGetAttribNode):
        dest = node.dest.var_name
        instance = node.instance.var_name
        attribute = node.attribute.var_name
        self.emit(f"    {dest} = GETATTR {instance} {attribute};")

    @visitor.when(cil.CILSetAttribNode)
    def visit(self, node:cil.CILSetAttribNode):
        instance = node.instance.var_name
        source = self.get_value(node.source)
        attribute = node.attribute.var_name
        self.emit(f"    SETATTR {instance} {attribute} {source};")

    @visitor.when(cil.CILGetIndexNode)
    def visit(self, node:cil.CILGetIndexNode):
        pass

    @visitor.when(cil.CILSetIndexNode)
    def visit(self, node:cil.CILSetIndexNode):
        pass

    @visitor.when(cil.CILAllocateNode)
    def visit(self, node:cil.CILAllocateNode):
        dest = node.dest.var_name
        type = node.type.class_name
        self.emit(f"    {dest} = ALLOCATE {type};")

    @visitor.when(cil.CILAllocateSelfNode)
    def visit(self, node:cil.CILAllocateSelfNode):
        dest = node.dest.var_name
        self.emit(f"    ALLOCATE_SELF {dest};")

    @visitor.when(cil.CILArrayNode)
    def visit(self, node:cil.CILArrayNode):
        pass

    @visitor.when(cil.CILTypeOfNode)
    def visit(self, node:cil.CILTypeOfNode):
        dest = node.dest.var_name
        source = node.source.var_name
        self.emit(f"    {dest} = TYPEOF {source};")

    @visitor.when(cil.CILLabelNode)
    def visit(self, node:cil.CILLabelNode):
        label = node.label.label_name
        self.emit(f"    LABEL: {label};")

    @visitor.when(cil.CILGotoNode)
    def visit(self, node:cil.CILGotoNode):
        label = node.label.label_name
        self.emit(f"    GOTO: {label};")

    @visitor.when(cil.CILGotoIfNode)
    def visit(self, node:cil.CILGotoIfNode):
        condition = self.get_value(node.condition)
        label = node.label.label_name
        self.emit(f"    IF {condition} GOTO {label};")

    @visitor.when(cil.CILStaticCallNode)
    def visit(self, node:cil.CILStaticCallNode):
        dest = node.dest.var_name
        function = node.function.method_name
        self.emit(f"    {dest} = CALL {function};")

    @visitor.when(cil.CILDinamicCallNode)
    def visit(self, node:cil.CILDinamicCallNode):
        dest = node.dest.var_name
        instance = node.instance.var_name
        function = node.function.method_name
        self.emit(f"    {dest} = VCALL {instance} {function};")

    @visitor.when(cil.CILArgNode)
    def visit(self, node:cil.CILArgNode):
        arg = node.arg.var_name
        self.emit(f"    ARG {arg};")

    @visitor.when(cil.CILReturnNode)
    def visit(self, node:cil.CILReturnNode):
        value = self.get_value(node.value)
        self.emit(f'    RETURN{f" {value}" if value else ""};')

    @visitor.when(cil.CILLoadNode)
    def visit(self, node:cil.CILLoadNode):
        dest = node.dest.var_name
        msg = node.msg.vname
        self.emit(f'    {dest} = LOAD {msg};')

    @visitor.when(cil.CILLengthNode)
    def visit(self, node:cil.CILLengthNode):
        dest = node.dest.var_name
        source = node.source.var_name
        self.emit(f'    {dest} = LENGTH {source};')

    @visitor.when(cil.CILConcatNode)
    def visit(self, node:cil.CILConcatNode):
        dest = node.dest.var_name
        left = node.left.var_name
        right = node.right.var_name
        self.emit(f'    {dest} = CONCAT {left} {right};')

    @visitor.when(cil.CILSubstringNode)
    def visit(self, node:cil.CILSubstringNode):
        dest = node.dest.var_name
        source = node.source.var_name
        idx = node.idx.var_name
        length = node.length.var_name
        self.emit(f'    {dest} = SUBSTR {source} {idx} {length};')

    @visitor.when(cil.CILReadStringNode)
    def visit(self, node: cil.CILReadStringNode):
        dest = node.dest.var_name
        self.emit(f'    {dest} = READ_STR;')

    @visitor.when(cil.CILReadIntNode)
    def visit(self, node: cil.CILReadIntNode):
        dest = node.dest.var_name
        self.emit(f'    {dest} = READ_INT;')

    @visitor.when(cil.CILPrintIntNode)
    def visit(self, node: cil.CILPrintIntNode):
        source = self.get_value(node.vinfo)
        self.emit(f'    PRINT_INT {source};')

    @visitor.when(cil.CILPrintStringNode)
    def visit(self, node: cil.CILPrintStringNode):
        source = node.str_addr.var_name
        self.emit(f'    PRINT_STR {source};')

    @visitor.when(cil.CILBoxNode)
    def visit(self, node: cil.CILBoxNode):
        dest = node.dest.var_name
        unboxed = self.get_value(node.unboxed_value)
        target_class = self.get_value(node.target_class)
        self.emit(f'    {dest} = BOX {unboxed} {target_class};')

    @visitor.when(cil.CILUnboxNode)
    def visit(self, node: cil.CILUnboxNode):
        boxed = self.get_value(node.boxed_value)
        self.emit(f'    UNBOX {boxed};')

    @visitor.when(cil.CILRuntimeErrorNode)
    def visit(self, node: cil.CILRuntimeErrorNode):
        self.emit(f'    RUNTIME_ERROR: {node.signal};')

    @visitor.when(cil.CILCopyNode)
    def visit(self, node:cil.CILCopyNode):
        dest = node.dest.var_name
        source = self.get_value(node.source)
        self.emit(f'    {dest} = COPY {source};')

    @visitor.when(cil.CILTypeNameNode)
    def visit(self, node:cil.CILTypeNameNode):
        dest = node.dest.var_name
        source = self.get_value(node.source)
        self.emit(f'    {dest} = TYPENAME {source};')

    @visitor.when(cil.CILDefaultValueNode)
    def visit(self, node:cil.CILDefaultValueNode):
        dest = node.dest.var_name
        self.emit(f'    {dest} = DEFAULT {node.type_name};')

    @visitor.when(cil.CILIsVoidNode)
    def visit(self, node:cil.CILIsVoidNode):
        dest = node.dest.var_name
        source = node.source.var_name
        self.emit(f'    {dest} = IS_VOID {source};')

    @visitor.when(cil.CILParentOfNode)
    def visit(self, node:cil.CILParentOfNode):
        dest = node.dest.var_name
        source = node.source.var_name
        self.emit(f'    {dest} = PARENTOF {source};')