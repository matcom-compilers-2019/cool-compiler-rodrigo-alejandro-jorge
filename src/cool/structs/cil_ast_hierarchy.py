class CILNode:
    pass

class CILProgramNode(CILNode):
    def __init__(self, dottypes, dotdata, dotcode):
        self.dottypes = dottypes
        self.dotdata = dotdata
        self.dotcode = dotcode

class CILTypeNode(CILNode):
    def __init__(self, class_info, attributes, functions):
        self.class_info = class_info
        self.attributes = attributes
        self.functions = functions

class CILDataNode(CILNode):
    def __init__(self, vname, value):
        self.vname = vname
        self.value = value

class CILFunctionNode(CILNode):
    def __init__(self, method_info, arguments, localvars, instructions):
        self.method_info = method_info
        self.arguments = arguments
        self.localvars = localvars
        self.instructions = instructions

class CILArgNode(CILNode):
    def __init__(self, arg):
        self.arg = arg

class CILLocalNode(CILNode):
    def __init__(self, vinfo):
        self.vinfo = vinfo

class CILInstructionNode(CILNode):
    pass

class CILAssignNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source

class CILArithmeticNode(CILInstructionNode):
    def __init__(self, dest, left, right):
        self.dest = dest
        self.left = left
        self.right = right

class CILPlusNode(CILArithmeticNode):
    pass

class CILMinusNode(CILArithmeticNode):
    pass

class CILStarNode(CILArithmeticNode):
    pass

class CILDivNode(CILArithmeticNode):
    pass

class CILLessNode(CILArithmeticNode):
    pass

class CILEqNode(CILArithmeticNode):
    pass

class CILStrEqNode(CILArithmeticNode):
    pass

class CILLessEqNode(CILArithmeticNode):
    pass

class CILGetAttribNode(CILInstructionNode):
    def __init__(self, dest, instance, attribute):
        self.dest = dest
        self.instance = instance
        self.attribute = attribute

class CILSetAttribNode(CILInstructionNode):
    def __init__(self, instance, attribute, source):
        self.instance = instance
        self.source = source
        self.attribute = attribute

class CILGetIndexNode(CILInstructionNode):
    def __init__(self, dest, array, index):
        self.dest = dest
        self.array = array
        self.index = index

class CILSetIndexNode(CILInstructionNode):
    def __init__(self, array, index, source):
        self.array = array
        self.index = index
        self.source = source

class CILAllocateNode(CILInstructionNode):
    def __init__(self, dest, type):
        self.dest = dest
        self.type = type

class CILAllocateSelfNode(CILInstructionNode):
    def __init__(self, dest):
        self.dest = dest

class CILArrayNode(CILInstructionNode):
    def __init__(self, dest, size):
        self.dest = dest
        self.size = size

class CILTypeOfNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source

class CILLabelNode(CILInstructionNode):
    def __init__(self, label):
        self.label = label

class CILGotoNode(CILInstructionNode):
    def __init__(self, label):
        self.label = label

class CILGotoIfNode(CILInstructionNode):
    def __init__(self, condition, label):
        self.condition = condition
        self.label = label

class CILStaticCallNode(CILInstructionNode):
    def __init__(self, dest, function):
        self.dest = dest
        self.function = function

class CILDinamicCallNode(CILInstructionNode):
    def __init__(self, dest, instance, function):
        self.dest = dest
        self.instance = instance
        self.function = function

class CILParamNode(CILInstructionNode):
    def __init__(self, vinfo):
        self.vinfo = vinfo

class CILReturnNode(CILInstructionNode):
    def __init__(self, value=None):
        self.value = value

class CILLoadNode(CILInstructionNode):
    def __init__(self, dest, msg):
        self.dest = dest
        self.msg = msg

class CILLengthNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source

class CILConcatNode(CILInstructionNode):
    def __init__(self, dest, left, right):
        self.dest = dest
        self.left = left
        self.right = right

class CILSubstringNode(CILInstructionNode):
    def __init__(self, dest, source, idx, length):
        self.dest = dest
        self.source = source
        self.idx = idx
        self.length = length

class CILReadStringNode(CILInstructionNode):
    def __init__(self, dest):
        self.dest = dest

class CILReadIntNode(CILInstructionNode):
    def __init__(self, dest):
        self.dest = dest

class CILPrintIntNode(CILInstructionNode):
    def __init__(self, vinfo):
        self.vinfo = vinfo

class CILPrintStringNode(CILInstructionNode):
    def __init__(self, str_addr):
        self.str_addr = str_addr

class CILBoxNode(CILInstructionNode):
    def __init__(self, dest, unboxed_value, target_class):
        self.dest = dest
        self.unboxed_value = unboxed_value
        self.target_class = target_class

class CILUnboxNode(CILInstructionNode):
    def __init__(self, boxed_value):
        self.boxed_value = boxed_value

class CILRuntimeErrorNode(CILInstructionNode):
    def __init__(self, signal):
        self.signal = signal

class CILCopyNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source

class CILTypeNameNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source

class CILDefaultValueNode(CILInstructionNode):
    def __init__(self, dest, type_name):
        self.dest = dest
        self.type_name = type_name

class CILIsVoidNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source

class CILParentOfNode(CILInstructionNode):
    def __init__(self, dest, source):
        self.dest = dest
        self.source = source
