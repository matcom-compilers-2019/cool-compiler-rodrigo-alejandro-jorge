import sys
from pathlib import Path

from cool.compiler.parser import Parser
from cool.compiler.checksemantics import CheckSemanticsVisitor
from cool.compiler.cool_to_cil import COOLToCILVisitor
from cool.compiler.cil_to_mips import CILToMIPSVisitor
from cool.utils.print_mips import MIPSWriterVisitor

def compile(input_file: Path, output_file: Path):
    program = input_file.read_text()

    #PARSING
    parser = Parser(build=True)
    ast = parser(program)
    ok = len(parser.errors) == 0

    if not ok:
        for err in parser.errors:
            print(err)
    else:
        #CHECK SEMANTICS
        checksemantics = CheckSemanticsVisitor()
        ok = checksemantics.visit(ast)

        if not ok:
            for err in checksemantics.errors:
                print(err)
        else:
            #COOL TO CIL
            cooltocil = COOLToCILVisitor(checksemantics.environment)
            cil_code = cooltocil.visit(ast)

            #CIL TO MIPS
            ciltomips = CILToMIPSVisitor()
            mips_code = ciltomips.visit(cil_code)

            #MIPS CODE
            mipswriter = MIPSWriterVisitor()
            mipswriter.visit(mips_code)
            output = '\n'.join(mipswriter.output)

            output_file.write_text(output)

if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = input_file[:-2]+"mips"
    compile(Path(input_file), Path(output_file))