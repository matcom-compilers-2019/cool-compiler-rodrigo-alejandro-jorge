from cool.utils.config import *
import cool.structs.cil_ast_hierarchy as cil
import cool.structs.mips_ast_hierarchy as mips
from cool.utils import visitor
from cool.structs.environment import *

#######################
#####VTABLE LAYOUT#####
#######################

#######################
#       type_name     # 0
#######################
#        parent       # 4
#######################
#         size        # 8
#######################
#       f1_label      # 12
#######################
#         ...         #
#         ...         #
#         ...         #
#######################
#       fn_label      # 4*(n+2)
#######################


#######################
####INSTANCE LAYOUT####
#######################

#######################
#       type_info     # 0
#######################
#       attr1_label   # 4
#######################
#         ...         #
#         ...         #
#         ...         #
#######################
#       attrn_label   # 4n
#######################


class CILToMIPSVisitor:
    def __init__(self):
        self.dotdata = []
        self.main_procedure = mips.MIPSProcedureNode("main")
        self.current_procedure = self.main_procedure
        self.dottext = [self.main_procedure]

        self.main_size = None

    def register_instruction(self, instruction_type, *args):
        instruction = instruction_type(*args)
        self.current_procedure.instructions.append(instruction)

    def register_empty(self):
        self.current_procedure.instructions.append(mips.MIPSEmptyInstruction())

    def register_comment(self, comment):
        self.current_procedure.instructions.append(mips.MIPSCommentNode(comment))

    def register_push(self, reg):
        self.register_instruction(mips.MIPSStoreWordNode, reg, 0, sp)
        self.register_instruction(mips.MIPSAddInmediateNode, sp, sp, -4)

    def register_pop(self, reg):
        self.register_instruction(mips.MIPSLoadWordNode, reg, 4, sp)
        self.register_instruction(mips.MIPSAddInmediateNode, sp, sp, 4)

    def register_data(self, data_type, *args):
        data = data_type(*args)
        self.dotdata.append(data)

    def register_main_allocation(self):
        self.register_comment("Allocating Main instance")
        self.register_instruction(mips.MIPSMoveNode, fp, sp)
        self.register_instruction(mips.MIPSAddInmediateNode, sp, sp, -4)
        self.allocate(0, "Main", self.main_size)
        self.register_empty()

        self.register_comment("Calling Main constructor")
        self.register_push(fp)
        self.register_instruction(mips.MIPSJumpAndLinkNode, "Main_constructor")
        self.register_empty()

        self.register_comment("Calling main method")
        self.register_instruction(mips.MIPSAddInmediateNode, sp, sp, -8)#pushing back main instance and fp
        self.register_instruction(mips.MIPSJumpAndLinkNode, "Main_main")

        self.register_instruction(mips.MIPSJumpNode, EXIT)
        self.register_empty()

    def generate_exception_messages(self):
        self.register_data(mips.MIPSDataTypedNode, ABORT_SIGNAL, ASCIIZ, ['"Program execution aborted"'])
        self.register_data(mips.MIPSDataTypedNode, CASE_MISSMATCH, ASCIIZ, ['"Execution of a case statement without a matching branch"'])
        self.register_data(mips.MIPSDataTypedNode, CASE_VOID, ASCIIZ, ['"Case on void"'])
        self.register_data(mips.MIPSDataTypedNode, DISPATCH_VOID, ASCIIZ, ['"Dispatch on void"'])
        self.register_data(mips.MIPSDataTypedNode, ZERO_DIVISION, ASCIIZ, ['"Division by zero"'])
        self.register_data(mips.MIPSDataTypedNode, SUBSTR_OUT_RANGE, ASCIIZ, ['"Substring out of range"'])
        self.register_data(mips.MIPSDataTypedNode, HEAP_OVERFLOW, ASCIIZ, ['"Heap overflow"'])

    def generate_extra_static_labels(self):
        self.register_data(mips.MIPSDataTypedNode, VOID, WORD, [-1])
        self.register_data(mips.MIPSDataTypedNode, EMPTY_STRING, ASCIIZ, ['""'])
        self.register_data(mips.MIPSDataTypedNode, INPUT_STR_BUFFER, SPACE, [BUFFER_SIZE])

    def generate_strcmp_code(self):
        self.current_procedure = mips.MIPSProcedureNode(STR_CMP)

        #comparing lengths
        self.register_instruction(mips.MIPSCommentNode, "Comparing lengths")
        self.register_instruction(mips.MIPSLoadWordNode, s0, LENGTH_ATTR_OFFSET, t0) #length offset
        self.register_instruction(mips.MIPSLoadWordNode, s1, LENGTH_ATTR_OFFSET, t1)
        self.register_instruction(mips.MIPSBranchOnNotEqualNode, s0, s1, "strcmp_neq")
        self.register_instruction(mips.MIPSEmptyInstruction)

        #comparing char by char
        self.register_instruction(mips.MIPSCommentNode, "Comparing char by char")
        self.register_instruction(mips.MIPSLoadWordNode, s0, CHARS_ATTR_OFFSET, t0) #char array pointer offset
        self.register_instruction(mips.MIPSLoadWordNode, s1, CHARS_ATTR_OFFSET, t1)
        self.register_instruction(mips.MIPSEmptyInstruction)

        #char by char loop
        self.register_instruction(mips.MIPSLabelNode, "strcmp_loop")
        self.register_instruction(mips.MIPSLoadByteNode, s2, 0, s0)
        self.register_instruction(mips.MIPSLoadByteNode, s3, 0, s1)
        self.register_instruction(mips.MIPSBranchOnNotEqualNode, s2, s3, "strcmp_neq")

        self.register_instruction(mips.MIPSBranchOnEqualNode, s2, zero, "strcmp_eq")
        self.register_instruction(mips.MIPSJumpNode, "strcmp_loop")
        self.register_instruction(mips.MIPSEmptyInstruction)

        self.register_instruction(mips.MIPSLabelNode, "strcmp_eq")
        self.register_instruction(mips.MIPSLoadInmediateNode, a0, 1)
        self.register_instruction(mips.MIPSJumpRegisterNode, ra)
        self.register_instruction(mips.MIPSEmptyInstruction)

        self.register_instruction(mips.MIPSLabelNode, "strcmp_neq")
        self.register_instruction(mips.MIPSLoadInmediateNode, a0, 0)
        self.register_instruction(mips.MIPSJumpRegisterNode, ra)
        self.register_instruction(mips.MIPSEmptyInstruction)

        self.dottext.append(self.current_procedure)

    def generate_abort(self):
        #falta imprimir el mensaje
        self.current_procedure = mips.MIPSProcedureNode(ABORT)

        self.register_comment("Printing message")
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_PRINT_STR)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_empty()

        self.register_comment("Aborting execution")
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_EXIT)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_empty()

        self.dottext.append(self.current_procedure)

    def generate_copy(self):
        #copies from t1 to t0 a0 bytes
        self.current_procedure = mips.MIPSProcedureNode(COPY)

        self.register_instruction(mips.MIPSLabelNode, "copy_loop")
        self.register_instruction(mips.MIPSBranchOnEqualNode, zero, a0, "copy_end")
        self.register_instruction(mips.MIPSLoadByteNode, t7, 0, t1)
        self.register_instruction(mips.MIPSStoreByteNode, t7, 0, t0)
        self.register_instruction(mips.MIPSAddInmediateNode, t0, t0, 1)
        self.register_instruction(mips.MIPSAddInmediateNode, t1, t1, 1)
        self.register_instruction(mips.MIPSAddInmediateNode, a0, a0, -1)
        self.register_instruction(mips.MIPSJumpNode, "copy_loop")
        self.register_empty()

        self.register_instruction(mips.MIPSLabelNode, "copy_end")
        self.register_instruction(mips.MIPSJumpRegisterNode, ra)
        self.register_empty()

        self.dottext.append(self.current_procedure)

    def generate_str_length(self):
        #calculates the length of the null-terminated char array referenced by $a0 and stores it in $a0
        self.current_procedure = mips.MIPSProcedureNode(LENGTH)

        self.register_instruction(mips.MIPSLoadInmediateNode, t6, 0)
        self.register_empty()

        self.register_instruction(mips.MIPSLabelNode, "length_loop")
        self.register_instruction(mips.MIPSLoadByteNode, t7, 0, a0)
        self.register_instruction(mips.MIPSBranchOnEqualNode, zero, t7, "length_end")

        self.register_instruction(mips.MIPSAddNode, t6, t6, 1)
        self.register_instruction(mips.MIPSAddNode, a0, a0, 1)
        self.register_instruction(mips.MIPSJumpNode, "length_loop")
        self.register_empty()

        self.register_instruction(mips.MIPSLabelNode, "length_end")
        self.register_instruction(mips.MIPSMoveNode, a0, t6)
        self.register_instruction(mips.MIPSJumpRegisterNode, ra)
        self.register_empty()

        self.dottext.append(self.current_procedure)

    def generate_auxiliar_procedures(self):
        self.generate_strcmp_code()
        self.generate_abort()
        self.generate_copy()
        self.generate_str_length()

    def generate_exit_program(self):
        self.current_procedure = mips.MIPSProcedureNode(EXIT)

        #que vamos a hacer

        self.dottext.append(self.current_procedure)

    def generate_type_extra_attributes(self, type):
        #this is the size of the object
        type.class_info.size = 4*(len(type.attributes) + INSTANCE_EXTRA_FIELDS)

        for i,attr in enumerate(type.attributes):
            attr.offset = 4*(i + INSTANCE_EXTRA_FIELDS)

        for i,func in enumerate(type.functions):
            func.vtable_offset = 4*(i + VTABLE_EXTRA_FIELDS)

    def generate_args_offsets(self, arguments):
        for i,arg in enumerate(arguments):
            arg.arg.offset = 4*(i + FP_ARGS_DISTANCE)

    def generate_locals_offsets(self, localvars):
        for i,local in enumerate(localvars):
            local.vinfo.offset = -4*(i + FP_LOCALS_DISTANCE)

    def allocate(self, dest_fp_offset, class_name, size):
        #allocating instance
        self.register_instruction(mips.MIPSLoadInmediateNode, a0, size)
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_SBRK)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSStoreWordNode, v0, dest_fp_offset, fp)

        #storing type info
        self.register_instruction(mips.MIPSLoadAdressNode, t0, class_name)
        self.register_instruction(mips.MIPSStoreWordNode, t0, TYPEINFO_ATTR_OFFSET, v0)

    def detect_case_on_void(self, fp_offset):
        self.register_comment("Capturing case on void")
        self.register_instruction(mips.MIPSLoadAdressNode, a0, CASE_VOID)
        self.register_instruction(mips.MIPSLoadWordNode, t0, fp_offset, fp)
        self.register_instruction(mips.MIPSLoadAdressNode, t1, VOID)
        self.register_instruction(mips.MIPSBranchOnEqualNode, t0, t1, ABORT)
        self.register_empty()

    def detect_dispatch_on_void(self):
        self.register_comment("Capturing dispatch on void")
        self.register_instruction(mips.MIPSLoadAdressNode, a0, DISPATCH_VOID)
        self.register_instruction(mips.MIPSLoadWordNode, t0, 4, sp)
        self.register_instruction(mips.MIPSLoadAdressNode, t1, VOID)
        self.register_instruction(mips.MIPSBranchOnEqualNode, t0, t1, ABORT)
        self.register_empty()

    def detect_substring_out_of_range(self, idx_fp_offset, length_fp_offset, source_fp_offset):
        self.register_comment("Capturing substr out of range")
        self.register_instruction(mips.MIPSLoadWordNode, s0, idx_fp_offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, s1, length_fp_offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, s3, source_fp_offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, s3, LENGTH_ATTR_OFFSET, s3)

        self.register_instruction(mips.MIPSLoadAdressNode, a0, SUBSTR_OUT_RANGE)

        self.register_instruction(mips.MIPSBranchOnLTNode, s0, zero, ABORT)
        self.register_instruction(mips.MIPSBranchOnLTNode, s1, zero, ABORT)
        self.register_instruction(mips.MIPSAddNode, s0, s0, s1)
        self.register_instruction(mips.MIPSBranchOnGTNode, s0, s3, ABORT)
        self.register_empty()

    def detect_division_by_zero(self, fp_offset):
        self.register_comment("Capturing division by zero")
        self.register_instruction(mips.MIPSLoadAdressNode, a0, ZERO_DIVISION)
        self.register_instruction(mips.MIPSLoadWordNode, t0, fp_offset, fp)
        self.register_instruction(mips.MIPSBranchOnEqualNode, t0, zero, ABORT)
        self.register_empty()



    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(cil.CILProgramNode)
    def visit(self, node:cil.CILProgramNode):
        for type in node.dottypes:
            self.visit(type)

        self.register_main_allocation()

        for data in node.dotdata:
            self.visit(data)

        self.generate_extra_static_labels()
        self.generate_exception_messages()

        self.generate_auxiliar_procedures()

        for func in node.dotcode:
            self.visit(func)

        self.generate_exit_program()

        return mips.MIPSProgramNode(self.dotdata, self.dottext)

    @visitor.when(cil.CILTypeNode)
    def visit(self, node:cil.CILTypeNode):
        self.generate_type_extra_attributes(node)
        length = len(node.functions) + VTABLE_EXTRA_FIELDS
        #this is type info data for current type
        self.register_data(mips.MIPSDataTypedNode, node.class_info.class_name, WORD, [-1]*length)
        self.register_data(mips.MIPSDataTypedNode, f'{node.class_info.class_name}_cname', ASCIIZ, [f'"{node.class_info.class_name}"'])

        self.register_comment(f"Filling {node.class_info.class_name} type info")
        #filling type info
        self.register_instruction(mips.MIPSLoadAdressNode, t0, node.class_info.class_name)
        self.register_empty()

        #class_name
        self.register_instruction(mips.MIPSLoadAdressNode, t1, f'{node.class_info.class_name}_cname')
        self.register_instruction(mips.MIPSStoreWordNode, t1, TYPENAME_OFFSET, t0)
        self.register_empty()
        #parent
        self.register_instruction(mips.MIPSLoadAdressNode, t1, node.class_info.ancestor.class_name if node.class_info.ancestor else node.class_info.class_name)
        self.register_instruction(mips.MIPSStoreWordNode, t1, PARENT_OFFSET, t0)
        self.register_empty()
        #size
        self.register_instruction(mips.MIPSLoadInmediateNode, t1, node.class_info.size)
        if node.class_info.class_name == "Main":
            self.main_size = node.class_info.size
        self.register_instruction(mips.MIPSStoreWordNode, t1, SIZE_OFFSET, t0)
        self.register_empty()

        self.register_comment(f"Filling {node.class_info.class_name} vtable")
        for func in node.functions:
            # print(func.method_name, func.vtable_offset)
            self.register_instruction(mips.MIPSLoadAdressNode, t1, func.method_name)
            self.register_instruction(mips.MIPSStoreWordNode, t1, func.vtable_offset, t0)
            self.register_empty()

    @visitor.when(cil.CILDataNode)
    def visit(self, node:cil.CILDataNode):
        self.register_data(mips.MIPSDataTypedNode, node.vname, ASCIIZ, [f'"{node.value}"'])

    @visitor.when(cil.CILFunctionNode)
    def visit(self, node: cil.CILFunctionNode):
        self.current_procedure = mips.MIPSProcedureNode(node.method_info.method_name)

        self.register_comment("Pushing $ra")
        self.register_push(ra)
        self.register_empty()

        self.register_comment("Saving $fp")
        self.register_instruction(mips.MIPSMoveNode, fp, sp)
        self.register_empty()

        self.register_comment("Reserving space for locals")
        self.register_instruction(mips.MIPSAddInmediateNode, sp, sp, -4*len(node.localvars))
        self.register_empty()

        self.generate_args_offsets(node.arguments)
        self.generate_locals_offsets(node.localvars)

        self.register_comment("Executing instructions")
        for inst in node.instructions:
            self.visit(inst)
            self.register_empty()

        self.register_comment("Restoring saved $ra")
        self.register_instruction(mips.MIPSLoadWordNode, ra, RA_OFFSET, fp)#stored $ra
        self.register_empty()

        self.register_comment("Restoring saved $fp")
        self.register_instruction(mips.MIPSLoadWordNode, fp, OLD_FP_OFFSET, fp)#stored (old)$fp
        self.register_empty()

        AR = 4*(len(node.localvars) + len(node.arguments) + 2)
        self.register_comment("Cleaning stack after call")
        self.register_instruction(mips.MIPSAddInmediateNode, sp, sp, AR)
        self.register_empty()

        self.register_comment("Return jump")
        self.register_instruction(mips.MIPSJumpRegisterNode, ra)
        self.register_empty()

        self.dottext.append(self.current_procedure)

    @visitor.when(cil.CILPlusNode)
    def visit(self, node: cil.CILPlusNode):
        self.register_comment("PlusNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSAddNode, t0, t0, t1)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILMinusNode)
    def visit(self, node: cil.CILMinusNode):
        self.register_comment("MinusNode")
        if isinstance(node.left, int):
            self.register_instruction(mips.MIPSLoadInmediateNode, t0, node.left)
        else:
            self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSSubstractNode, t0, t0, t1)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILStarNode)
    def visit(self, node: cil.CILStarNode):
        self.register_comment("MulNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSMultiplyNode, t0, t1)
        self.register_instruction(mips.MIPSMLONode,t0)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILDivNode)
    def visit(self, node: cil.CILDivNode):
        self.register_comment("DivideNode")

        self.detect_division_by_zero(node.right.offset)

        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSDivideNode, t0, t1)
        self.register_instruction(mips.MIPSMLONode,t0)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILLessNode)
    def visit(self, node: cil.CILLessNode):
        self.register_comment("LessNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSSetOnLTNode, t0, t0, t1)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILLessEqNode)
    def visit(self, node: cil.CILLessEqNode):
        self.register_comment("LessEqNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSSetOnLTENode, t0, t0, t1)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILEqNode)
    def visit(self, node: cil.CILEqNode):
        self.register_comment("EqNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        if isinstance(node.right, ClassInfo):#esto es un convenio con el case
            self.register_instruction(mips.MIPSLoadAdressNode, t1, node.right.class_name)
        else:
            self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSSetOnENode, t0, t0, t1)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILStrEqNode)
    def visit(self, node: cil.CILStrEqNode):
        self.register_comment("StrEqNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)

        self.register_instruction(mips.MIPSJumpAndLinkNode, STR_CMP)
        self.register_instruction(mips.MIPSStoreWordNode, a0, node.dest.offset, fp)

    @visitor.when(cil.CILAssignNode)
    def visit(self, node: cil.CILAssignNode):
        self.register_comment("AssignNode")
        if isinstance(node.source, int):
            self.register_instruction(mips.MIPSLoadInmediateNode, t0, node.source)
        else:
            self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILLabelNode)
    def visit(self, node: cil.CILLabelNode):
        self.register_comment("LabelNode")
        self.register_empty()
        self.register_instruction(mips.MIPSLabelNode, node.label.label_name)

    @visitor.when(cil.CILGotoNode)
    def visit(self, node: cil.CILGotoNode):
        self.register_instruction(mips.MIPSJumpNode, node.label.label_name)

    @visitor.when(cil.CILGotoIfNode)
    def visit(self, node: cil.CILGotoIfNode):
        self.register_comment("GotoIfNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.condition.offset, fp)
        self.register_instruction(mips.MIPSBranchNeqZero, t0, node.label.label_name)

    @visitor.when(cil.CILGetAttribNode)
    def visit(self, node: cil.CILGetAttribNode):
        self.register_comment("GetAttribNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.instance.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.attribute.offset, t0)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILSetAttribNode)
    def visit(self, node: cil.CILSetAttribNode):
        self.register_comment("SetAttribNode")
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.instance.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.attribute.offset, t1)

    @visitor.when(cil.CILAllocateNode)
    def visit(self, node: cil.CILAllocateNode):
        self.register_comment("AllocateNode")
        self.allocate(node.dest.offset, node.type.class_name, node.type.size)

    @visitor.when(cil.CILAllocateSelfNode)
    def visit(self, node: cil.CILAllocateSelfNode):
        self.register_comment("AllocateSelfNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, SELF_OFFSET, fp) # esta es la direccion de self
        self.register_instruction(mips.MIPSLoadWordNode, t0, TYPEINFO_ATTR_OFFSET, t0) # esta es la direccion a la type_info
        self.register_instruction(mips.MIPSLoadWordNode, a0, SIZE_OFFSET, t0) # esta es la direccion del size de self
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_SBRK)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSStoreWordNode, v0, node.dest.offset, fp)

        #storing type info
        self.register_instruction(mips.MIPSStoreWordNode, t0, TYPEINFO_ATTR_OFFSET, v0)

    @visitor.when(cil.CILTypeOfNode)
    def visit(self, node: cil.CILTypeOfNode):
        self.register_comment("TypeOfNode")

        self.detect_case_on_void(node.source.offset)

        #executing typeof
        self.register_comment("Executing typeof")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, TYPEINFO_ATTR_OFFSET, t0)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILParentOfNode)
    def visit(self, node: cil.CILParentOfNode):
        self.register_comment("ParentOfNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, PARENT_OFFSET, t0)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILParamNode)
    def visit(self, node: cil.CILParamNode):
        self.register_comment("ParamNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.vinfo.offset, fp)
        self.register_push(t0)

    @visitor.when(cil.CILStaticCallNode)
    def visit(self, node: cil.CILStaticCallNode):
        self.register_comment("StaticCallNode")

        self.detect_dispatch_on_void()

        self.register_push(fp)
        self.register_instruction(mips.MIPSJumpAndLinkNode, node.function.method_name)
        self.register_instruction(mips.MIPSStoreWordNode, a0, node.dest.offset, fp)

    @visitor.when(cil.CILDinamicCallNode)
    def visit(self, node: cil.CILDinamicCallNode):
        self.register_comment("DynamicCallNode")

        self.detect_dispatch_on_void()

        self.register_push(fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.instance.offset, fp) #instance address
        self.register_instruction(mips.MIPSLoadWordNode, t0, TYPEINFO_ATTR_OFFSET, t0) #instance type_info
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.function.vtable_offset, t0) #function pointer
        self.register_instruction(mips.MIPSJumpAndLinkRegNode, t0)
        self.register_instruction(mips.MIPSStoreWordNode, a0, node.dest.offset, fp)

    @visitor.when(cil.CILReturnNode)
    def visit(self, node: cil.CILReturnNode):
        self.register_comment("ReturnNode")
        self.register_instruction(mips.MIPSLoadWordNode, a0, node.value.offset, fp)

    @visitor.when(cil.CILRuntimeErrorNode)
    def visit(self, node: cil.CILRuntimeErrorNode):
        self.register_instruction(mips.MIPSLoadAdressNode, a0, node.signal)
        self.register_instruction(mips.MIPSJumpNode, ABORT)

    @visitor.when(cil.CILBoxNode)
    def visit(self, node: cil.CILBoxNode):
        self.register_comment("BoxNode")
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.unboxed_value.offset, fp)
        if node.target_class == INT:
            self.allocate(node.dest.offset, INT, BOX_SIZE)
        else:
            self.allocate(node.dest.offset, BOOL, BOX_SIZE)
        self.register_instruction(mips.MIPSStoreByteNode, t1, BOXED_VALUE_OFFSET, v0)#storing at te value attribute of the instance

    @visitor.when(cil.CILUnboxNode)
    def visit(self, node: cil.CILUnboxNode):
        self.register_comment("UnboxNode")
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.boxed_value.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, BOXED_VALUE_OFFSET, t1)
        self.register_instruction(mips.MIPSStoreWordNode, t1, node.boxed_value.offset, fp)

    @visitor.when(cil.CILDefaultValueNode)
    def visit(self, node: cil.CILDefaultValueNode):
        self.register_comment("DefaultValueNode")
        if node.type_name in [INT,BOOL]:
            self.register_instruction(mips.MIPSLoadInmediateNode, t0, 0)
            self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)
        elif node.type_name == STRING:
            self.allocate(node.dest.offset, STRING, STRING_SIZE)
            self.register_instruction(mips.MIPSLoadInmediateNode, t0, 0)
            self.register_instruction(mips.MIPSStoreWordNode, t0, LENGTH_ATTR_OFFSET, v0)
            self.register_instruction(mips.MIPSLoadAdressNode, t0, EMPTY_STRING)
            self.register_instruction(mips.MIPSStoreWordNode, t0, CHARS_ATTR_OFFSET, v0)
        else:
            self.register_instruction(mips.MIPSLoadAdressNode, t0, VOID)
            self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILIsVoidNode)
    def visit(self, node: cil.CILIsVoidNode):
        self.register_comment("IsVoidNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadAdressNode, t1, VOID)
        self.register_instruction(mips.MIPSSetOnENode, t0, t0, t1) # aqui no seria SetOnEqNode?
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    #string stuff
    @visitor.when(cil.CILLoadNode)
    def visit(self, node: cil.CILLoadNode):
        self.register_comment("LoadNode")
        self.allocate(node.dest.offset, STRING, STRING_SIZE)

        #storing string length
        self.register_instruction(mips.MIPSLoadInmediateNode, t0, len(node.msg.value))
        self.register_instruction(mips.MIPSStoreWordNode, t0, LENGTH_ATTR_OFFSET, v0)

        #storing string chars ref
        self.register_instruction(mips.MIPSLoadAdressNode, t0, node.msg.vname)
        self.register_instruction(mips.MIPSStoreWordNode, t0, CHARS_ATTR_OFFSET, v0)

    @visitor.when(cil.CILLengthNode)
    def visit(self, node: cil.CILLengthNode):
        self.register_comment("LengthNode")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, LENGTH_ATTR_OFFSET, t0)
        self.register_instruction(mips.MIPSStoreWordNode, t0, node.dest.offset, fp)

    @visitor.when(cil.CILSubstringNode)
    def visit(self, node: cil.CILSubstringNode):
        self.register_comment("SubstringNode")

        self.detect_substring_out_of_range(node.idx.offset, node.length.offset, node.source.offset)

        #allocating new char array
        self.register_comment("Allocating new char array")
        self.register_instruction(mips.MIPSLoadWordNode, s0, node.length.offset, fp)#salvando el length del substr
        self.register_instruction(mips.MIPSMoveNode, a0, s0)
        self.register_instruction(mips.MIPSAddInmediateNode, a0, a0, 1)
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_SBRK)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSMoveNode, t0, v0)#saving the dest char arr in t0
        self.register_empty()

        #loading ref to char array of source string
        self.register_comment("Loading reference to char array of source string")
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, CHARS_ATTR_OFFSET, t1)
        self.register_instruction(mips.MIPSLoadWordNode, s2, node.idx.offset, fp)
        self.register_instruction(mips.MIPSAddNode, t1, t1, s2)#saving the source char arr in t1

        self.register_instruction(mips.MIPSMoveNode, s1, t0)
        self.register_empty()

        #this copies from t1 to t0 a0 bytes
        self.register_comment("Copying bytes from one char array to another")
        self.register_instruction(mips.MIPSMoveNode, a0, s0)
        self.register_instruction(mips.MIPSJumpAndLinkNode, COPY)
        self.register_empty()

        self.register_comment("Null-terminating the string")
        self.register_instruction(mips.MIPSStoreByteNode, zero, 0, t0)
        self.register_empty()

        self.register_comment("Allocating new String instance")
        self.allocate(node.dest.offset, STRING, STRING_SIZE)
        self.register_empty()

        #storing string length
        self.register_comment("Storing length and reference to char array")
        self.register_instruction(mips.MIPSLoadWordNode, s0, node.length.offset, fp)
        self.register_instruction(mips.MIPSStoreWordNode, s0, LENGTH_ATTR_OFFSET, v0)

        #storing string chars ref
        self.register_instruction(mips.MIPSStoreWordNode, s1, CHARS_ATTR_OFFSET, v0)
        self.register_empty()

    @visitor.when(cil.CILConcatNode)
    def visit(self, node: cil.CILConcatNode):
        #cargar los length
        self.register_comment("Loading length")
        self.register_instruction(mips.MIPSLoadWordNode, s1, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, s1, LENGTH_ATTR_OFFSET, s1)
        self.register_instruction(mips.MIPSLoadWordNode, s2, node.right.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, s2, LENGTH_ATTR_OFFSET, s2)

        self.register_instruction(mips.MIPSAddNode, t2, s1, s2)
        self.register_empty()

        #crear el nuevo array de bytes
        self.register_comment("Allocating new char array")
        self.register_instruction(mips.MIPSMoveNode, a0, t2)
        self.register_instruction(mips.MIPSAddInmediateNode, a0, a0, 1)
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_SBRK)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSMoveNode, t0, v0)#saving the dest char arr in t0
        self.register_instruction(mips.MIPSMoveNode, t3, v0)
        self.register_empty()

        self.register_comment("Copying bytes from first string")
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.left.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, CHARS_ATTR_OFFSET, t1)
        self.register_instruction(mips.MIPSMoveNode, a0, s1)
        self.register_instruction(mips.MIPSJumpAndLinkNode, COPY)
        self.register_empty()

        self.register_comment("Copying bytes from second string")
        self.register_instruction(mips.MIPSLoadWordNode, t1, node.right.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t1, CHARS_ATTR_OFFSET, t1)
        self.register_instruction(mips.MIPSMoveNode, a0, s2)
        self.register_instruction(mips.MIPSJumpAndLinkNode, COPY)
        self.register_empty()

        self.register_comment("Null-terminating the string")
        self.register_instruction(mips.MIPSStoreByteNode, zero, 0, t0)
        self.register_empty()

        self.register_comment("Allocating new String instance")
        self.allocate(node.dest.offset, STRING, STRING_SIZE)
        self.register_empty()

        #storing string length
        self.register_comment("Storing length and reference to char array")
        self.register_instruction(mips.MIPSStoreWordNode, t2, LENGTH_ATTR_OFFSET, v0)

        #storing string chars ref
        self.register_instruction(mips.MIPSStoreWordNode, t3, CHARS_ATTR_OFFSET, v0)

    @visitor.when(cil.CILPrintStringNode)
    def visit(self, node: cil.CILPrintStringNode):
        self.register_comment("PrintStringNode")
        self.register_instruction(mips.MIPSLoadWordNode, a0, node.str_addr.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, a0, CHARS_ATTR_OFFSET, a0)
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_PRINT_STR)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_empty()

    @visitor.when(cil.CILReadStringNode)
    def visit(self, node: cil.CILReadStringNode):
        self.register_comment("ReadStringNode")
        self.register_comment("Reading string to buffer")
        self.register_instruction(mips.MIPSLoadAdressNode, a0, INPUT_STR_BUFFER)
        self.register_instruction(mips.MIPSLoadInmediateNode, a1, BUFFER_SIZE)
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_READ_STR)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_empty()

        self.register_comment("Saving reference to read string")
        self.register_instruction(mips.MIPSMoveNode, t1, a0)
        self.register_empty()

        self.register_comment("Calculating str length")
        self.register_instruction(mips.MIPSJumpAndLinkNode, LENGTH)
        self.register_empty()

        self.register_comment("Allocating char array for new string")
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_SBRK)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSMoveNode, t0, v0)
        self.register_instruction(mips.MIPSMoveNode, t3, v0)#saving pointer to char array

        self.register_instruction(mips.MIPSAddInmediateNode, a0, a0, -1)
        self.register_instruction(mips.MIPSMoveNode, t2, a0)#saving length

        self.register_comment("Copying bytes from one char array to another")
        self.register_instruction(mips.MIPSJumpAndLinkNode, COPY)
        self.register_empty()

        self.register_comment("Null-terminating the string")
        self.register_instruction(mips.MIPSStoreByteNode, zero, 0, t0)
        self.register_empty()

        self.register_comment("Allocating new String instance")
        self.allocate(node.dest.offset, STRING, STRING_SIZE)
        self.register_empty()

        #storing string length
        self.register_comment("Storing length and reference to char array")
        self.register_instruction(mips.MIPSStoreWordNode, t2, LENGTH_ATTR_OFFSET, v0)

        #storing string chars ref
        self.register_instruction(mips.MIPSStoreWordNode, t3, CHARS_ATTR_OFFSET, v0)

    #object stuff
    @visitor.when(cil.CILTypeNameNode)
    def visit(self, node: cil.CILTypeNameNode):
        self.register_comment("TypeNameNode")

        self.register_comment("Allocating new String instance")
        self.allocate(node.dest.offset, STRING, STRING_SIZE)
        self.register_instruction(mips.MIPSStoreWordNode, v0, node.dest.offset, fp)
        self.register_empty()

        self.register_comment("Determining length")
        self.register_instruction(mips.MIPSLoadWordNode, t0, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, t0, TYPEINFO_ATTR_OFFSET, t0)
        self.register_instruction(mips.MIPSLoadWordNode, a0, TYPENAME_OFFSET, t0)
        self.register_instruction(mips.MIPSMoveNode, a1, a0)
        self.register_instruction(mips.MIPSJumpAndLinkNode, LENGTH)
        self.register_empty()

        self.register_comment("Storing length and reference to char array")
        self.register_instruction(mips.MIPSStoreWordNode, a0, LENGTH_ATTR_OFFSET, v0)#storing the length
        self.register_instruction(mips.MIPSStoreWordNode, a1, CHARS_ATTR_OFFSET, v0)#storing the char array reference

    @visitor.when(cil.CILCopyNode)
    def visit(self, node: cil.CILCopyNode):
        self.register_comment("CopyNode")

        self.register_instruction(mips.MIPSLoadWordNode, t1, node.source.offset, fp)
        self.register_instruction(mips.MIPSLoadWordNode, a0, TYPEINFO_ATTR_OFFSET, t1)
        self.register_instruction(mips.MIPSLoadWordNode, a0, SIZE_OFFSET, a0)

        #allocating space for copied instance
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_SBRK)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSStoreWordNode, v0, node.dest.offset, fp)

        self.register_instruction(mips.MIPSMoveNode, t0, v0)

        self.register_instruction(mips.MIPSJumpAndLinkNode, COPY)

    #io stuff
    @visitor.when(cil.CILReadIntNode)
    def visit(self, node: cil.CILReadIntNode):
        self.register_comment("ReadIntNode")
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_READ_INT)
        self.register_instruction(mips.MIPSSyscallNode)
        self.register_instruction(mips.MIPSStoreWordNode, v0, node.dest.offset, fp)

    @visitor.when(cil.CILPrintIntNode)
    def visit(self, node: cil.CILPrintIntNode):
        self.register_comment("PrintInt")
        self.register_instruction(mips.MIPSLoadWordNode, a0, node.vinfo.offset, fp)
        self.register_instruction(mips.MIPSLoadInmediateNode, v0, SYSCALL_PRINT_INT)
        self.register_instruction(mips.MIPSSyscallNode)
