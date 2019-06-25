from cool.utils.config import *
import cool.structs.mips_ast_hierarchy as mips
from cool.utils import visitor

class MIPSWriterVisitor(object):
    def __init__(self):
        self.tabs = 0
        self.output = []

    def emit(self, msg):
        self.output.append(self.tabs*" " + msg)

    def black(self):
        self.output.append('')

    def visit(self, node:mips.MIPSProgramNode):
        self.emit(".data")
        self.black()
        for data in node.dotdata:
            self.emit(str(data))

        self.black()
        self.emit(".text")
        self.emit(".globl main")
        self.black()
        for proc in node.dottext:
            self.emit(f'{proc.label}:')
            self.tabs += 4
            for inst in proc.instructions:
                self.emit(str(inst))
            self.tabs -= 4
