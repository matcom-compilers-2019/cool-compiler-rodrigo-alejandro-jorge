from cool.utils import visitor
from functools import reduce
from cool.structs import cool_ast_hierarchy as ast
import itertools as itl
from cool.utils.config import *

#como chequear lo de defaults values

class BuildObjectsEnvironmentVisitor:
    def __init__(self, environment, errors):
        self.errors = errors
        self.environment = environment

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.ProgramNode)
    def visit(self, node):
        ok = True
        for cl in node.class_list:
            ok &= self.visit(cl)
        return ok

    @visitor.when(ast.ClassNode)
    def visit(self, node):
        ok = False
        self.environment.enter_in_class(node.class_name)
        cname = node.class_name
        if cname == "SELF_TYPE":
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, "Invalid class identifier 'SELF_TYPE'."))
        elif node.ancestor == "SELF_TYPE":
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, "Invalid use of 'SELF_TYPE'."))
        elif node.ancestor in [INT, BOOL, STRING]:
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, "Class cannot inherit from Int, Bool or String."))
        elif self.environment.is_class_defined(cname):
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, f"Class '{cname}' already defined."))
        else:
            self.environment.define_class(cname, node.ancestor)
            ok = True
        return ok

class BuildMethodsEnvironmentVisitor:
    def __init__(self, environment, errors):
        self.environment = environment
        self.errors = errors

    @visitor.on('node')
    def visit(self,node):
        pass

    @visitor.when(ast.ProgramNode)
    def visit(self,node):
        ok = True
        for cl in node.class_list:
            ok &= self.visit(cl)
        return ok

    @visitor.when(ast.ClassNode)
    def visit(self, node):
        self.environment.enter_in_class(node.class_name)
        ok = True
        for attr in node.attrs_list:
            ok &= self.visit(attr)
        for method in node.methods_list:
            ok &= self.visit(method)
        return ok

    @visitor.when(ast.MethodDefinitionNode)
    def visit(self, node):
        ok=True
        mname = node.method_name

        signature=[x[1] for x in node.signature] #quedandome con el nombre de ls tipos nada mas
        signature.append(node.return_type)

        if self.environment.is_method_defined_in_class(mname):
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, f"Method {mname} already defined in class."))
            ok = False
        else:
            for type in signature:
                if type != SELF_TYPE and not self.environment.is_class_defined(type):
                    self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, f"Class '{type}' is not defined."))
                    ok = False
            method_in_ancestor = self.environment.get_method_info(mname)
            if method_in_ancestor and not self.environment.same_signatures(method_in_ancestor.signature, signature):
                self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, f"Redefined method has not the same signature as the original one."))
                ok = False
            self.environment.define_method_in_class(mname, signature)
        return ok

    @visitor.when(ast.AttributeDeclarationNode)
    def visit(self, node):
        ok=False
        attr_name = node.attr_name
        type_name = node.attr_type
        if self.environment.is_attr_defined(attr_name):
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, f"Attribute '{attr_name}' already defined."))
        elif attr_name == "self":
            self.errors.append(Error(node.row, node.column, SEMANTIC_ERROR, f"Invalid attribute identifier 'self'."))
        else:
            node.variable_info = self.environment.define_attr_in_class(attr_name, type_name)
            ok = True
        return ok

#errores:
#dependencia ciclica---
#clases repetidas---
#metodos repetidos---
#metodos redefinidos mal---
#signatura correcta de los metodos---
#clases que se llamen SELF_TYPE---
#si existe la clase Main---
#si existe el metodo main en la clase Main con la signatura adecuada---
#atributos repetidos---
#atributo que se llame self---
#herencia de Int, Bool, String---
class Environment:
    def __init__(self, errors):
        self.types={}
        self.current_class_name=None
        self.scope=Scope()
        self.add_predefined_types()
        self.errors = errors

        #LCA stuff
        #ancestors es un dict q guarda para cada tipo un array q en la posicion i-esima tiene
        #el elemento q esta 2^i posiciones mas arriba en la jerarquia
        #depths es un diccionario q para cada tipo guarda la profundidad del nodo en la
        #jerarquia de clases
        #discover y finish tienen los tiempos de descubrimiento y finalizacion de los tipos en el DFS
        self.lca_utils={"ancestors":{},"depths":{}, "discover":{}, "finish":{}}

    #API
    def build_env(self, ast):
        visitor = BuildObjectsEnvironmentVisitor(self, self.errors)
        if visitor.visit(ast):
            self.build_hierarchy_tree()
            if self.check_cyclic_hierarchy():
                self.LCA_preproc()
                visitor = BuildMethodsEnvironmentVisitor(self, self.errors)
                return visitor.visit(ast) and self.check_main_class_issues()
            else:
                return False
        else:
            return False

    def enter_in_class(self, class_name):
        self.current_class_name=class_name

    def is_class_defined(self,class_name):
        return class_name in self.types

    def is_method_defined(self, method_name, class_name=None):
        class_name = class_name if class_name else self.current_class_name
        return self.get_method_info(method_name, class_name) is not None

    def is_attr_defined(self,attr_name, class_name=None):
        class_name=class_name if class_name else self.current_class_name
        return self.get_attr_info(attr_name, class_name) is not None

    def is_local(self, var_name):
        return self.scope.is_local(var_name)

    def is_variable_defined(self, var_name):
        return self.scope.is_defined(var_name)

    def get_method_info(self, method_name, class_name=None):
        class_name = class_name if class_name else self.current_class_name
        cl=self.types[class_name]
        while not (cl is None):
            class_name=cl.class_name
            if self.is_method_defined_in_class(method_name, class_name):
                return self.types[class_name].methods[method_name]
            else:
                cl=cl.ancestor

    def get_attr_info(self, attr_name, class_name=None):
        class_name=class_name if class_name else self.current_class_name
        cl=self.types[class_name]
        while not (cl is None):
            class_name=cl.class_name
            if self.is_attr_defined_in_class(attr_name, class_name):
                return self.types[class_name].attrs[attr_name]
            else:
                cl=cl.ancestor

    def get_variable_info(self, var_name):
        return self.scope.get_variable_info(var_name)

    def define_variable(self, var_name, type):
        return self.scope.define_variable(var_name, type)

    def create_child_scope(self):
        self.scope = self.scope.create_child_scope()

    def checkout_parent_scope(self):
        self.scope = self.scope.parent

    def same_signatures(self, sig1, sig2):
        if len(sig1) == len(sig2):
            for s1,s2 in zip(sig1, sig2):
                if s1 != s2:
                    return False
        return True

    #Utils

    def join_types(self, types):
        def LCA(type1,type2):
            if type1 == type2 and type1 == SELF_TYPE:
                return type1
            if type1 == SELF_TYPE:
                type1 = self.current_class_name
            if type2 == SELF_TYPE:
                type2 = self.current_class_name

            type1 = type1 if isinstance(type1,ClassInfo) else self.types[type1]
            type2 = type2 if isinstance(type2,ClassInfo) else self.types[type2]

            if type1.class_name==OBJECT or type2.class_name==OBJECT:
                return self.types[OBJECT].class_name

            if self.is_ancestor(type1, type2):
                return type1.class_name
            if self.is_ancestor(type2, type1):
                return type2.class_name

            ancestors=self.lca_utils["ancestors"]
            depths=self.lca_utils["depths"]

            i1 = len(ancestors[type1.class_name]) - 1
            i2 = len(ancestors[type2.class_name]) - 1
            while type1.ancestor.class_name!=type2.ancestor.class_name:
                deepest_type=type1 if depths[type1.class_name]>depths[type2.class_name] else type2
                if deepest_type.class_name==type1.class_name:
                    while self.is_ancestor(self.types[ancestors[type1.class_name][i1].class_name], type2):
                        i1-=1
                    type1=self.types[ancestors[type1.class_name][i1].class_name]
                else:
                    while self.is_ancestor(self.types[ancestors[type2.class_name][i2].class_name], type1):
                        i2-=1
                    type2=self.types[ancestors[type2.class_name][i2].class_name]
            return type1.ancestor.class_name
        return reduce(LCA,types)#reduce is defined in functools library

    def conforms_to(self,child_class_name, parent_class_name):
        if parent_class_name == SELF_TYPE:
            return child_class_name == SELF_TYPE
        if child_class_name == SELF_TYPE:
            child_class_name = self.current_class_name

        return self.is_ancestor(parent_class_name,child_class_name)


    #Private
    def LCA_preproc(self):
        ancestors=self.lca_utils["ancestors"]
        depths=self.lca_utils["depths"]
        depths[OBJECT]=0
        d=self.lca_utils["discover"]
        f=self.lca_utils["finish"]
        stack=[]
        time=0

        #inicializa ancestors y depths
        def LCA_dfs_visit(type):
            nonlocal time #por la porqueria de clausura de python
            time+=1
            d[type.class_name]=time
            stack.append(type)
            pow=1
            ancestors[type.class_name]=[]
            while (len(stack)-pow)>0:
                ancestors[type.class_name].append(stack[-1-pow])
                pow*=2
            for child in type.siblings:
                depths[child.class_name]=depths[type.class_name]+1
                LCA_dfs_visit(child)

            time+=1
            f[type.class_name]=time
            stack.pop()

        object=self.types[OBJECT]
        LCA_dfs_visit(object)

    #works well wether type1, type2 are ClassInfo's of just the string name's
    def is_ancestor(self, type1, type2):
        name1 = type1.class_name if isinstance(type1,ClassInfo) else type1
        name2 = type2.class_name if isinstance(type2,ClassInfo) else type2
        d = self.lca_utils["discover"]
        f = self.lca_utils["finish"]
        return type1 == type2 or (d[name1]<d[name2] and f[name2]<f[name1])

    def is_method_defined_in_class(self,method_name, class_name=None):
        class_name=class_name if class_name else self.current_class_name
        return class_name in self.types and method_name in self.types[class_name].methods and self.types[class_name].methods[method_name] is not None

    def is_attr_defined_in_class(self,attr_name, class_name=None):
        class_name=class_name if class_name else self.current_class_name
        return class_name in self.types and attr_name in self.types[class_name].attrs and self.types[class_name].attrs[attr_name] is not None

    def define_class(self,class_name,inherits_from=OBJECT):
        self.types[class_name]=ClassInfo(class_name,inherits_from)
        return self.types[class_name]

    def define_method_in_class(self, method_name, signature, class_name=None):
        class_name=class_name if class_name else self.current_class_name
        self.types[class_name].methods[method_name]=MethodInfo(method_name,signature)
        return self.types[class_name].methods[method_name]

    def define_attr_in_class(self, attr_name, type_name, class_name=None):
        class_name=class_name if class_name else self.current_class_name
        self.types[class_name].attrs[attr_name]=VariableInfo(attr_name,type_name, True)
        return self.types[class_name].attrs[attr_name]

    def add_predefined_types(self):
        #Object
        object = ClassInfo(OBJECT, None)
        abort = MethodInfo(ABORT,[OBJECT])
        type_name = MethodInfo(TYPE_NAME, [STRING])
        copy = MethodInfo(COPY, [SELF_TYPE])
        object.methods = {ABORT:abort, TYPE_NAME:type_name, COPY:copy}
        self.types[OBJECT] = object

        #IO
        io=ClassInfo(IO, OBJECT)
        out_string = MethodInfo(OUT_STRING, [STRING, SELF_TYPE])
        out_int = MethodInfo(OUT_INT, [INT, SELF_TYPE])
        in_string = MethodInfo(IN_STRING, [STRING])
        in_int = MethodInfo(IN_INT, [INT])
        io.methods = {OUT_STRING:out_string, OUT_INT:out_int, IN_STRING:in_string, IN_INT:in_int}
        self.types[IO] = io

        #Int
        intc = ClassInfo(INT, OBJECT)
        self.types[INT] = intc

        #Bool
        boolc = ClassInfo(BOOL, OBJECT)
        self.types[BOOL] = boolc

        #String
        string = ClassInfo(STRING, OBJECT)
        length = MethodInfo(LENGTH, [INT])
        concat = MethodInfo(CONCAT, [STRING, STRING])
        substr = MethodInfo(SUBSTR, [INT, INT, STRING])
        string.methods = {LENGTH:length, CONCAT:concat, SUBSTR:substr}
        self.types[STRING] = string

    #Semantic checks
    def build_hierarchy_tree(self):
        for (class_name,class_info) in self.types.items():
            if class_name != OBJECT:
                ancestor_info = self.types[class_info.ancestor] if class_info.ancestor in self.types else None
                class_info.ancestor = ancestor_info
                if ancestor_info is not None:#esto pasa cuando se hereda de una clase q no esta definida
                    ancestor_info.siblings.append(class_info)

    def check_cyclic_hierarchy(self):#BFS
        visited = {class_info.class_name: False for _,class_info in self.types.items()}
        for _,cl in self.types.items():
            if not visited[cl.class_name]:
                queue=[cl]
                while len(queue)>0:
                    class_info=queue.pop(0)
                    if visited[class_info.class_name]:
                        self.errors.append(Error(0,0, SEMANTIC_ERROR, f"Circular inheritance dependency including class {class_info.class_name}."))
                        return False
                    visited[class_info.class_name] = True
                    queue.extend(class_info.siblings)
        return True

    def check_main_class_issues(self):
        ok = False
        if not self.is_class_defined("Main"):
            self.errors.append(Error(0, 0, SEMANTIC_ERROR, "'Main' class in not defined."))
        elif not self.is_method_defined_in_class("main", "Main"):
            self.errors.append(Error(0, 0, SEMANTIC_ERROR, "'main' method is not defined in class 'Main'."))
        elif not len(self.get_method_info("main", "Main").signature) == 1:
            self.errors.append(Error(0, 0, SEMANTIC_ERROR, "Wrong signature for 'main' method in class 'Main'."))
        else:
            ok = True
        return ok

class Scope:
    def __init__(self, parent=None):
        self.locals = []
        self.parent = parent
        self.children = []
        self.index_at_parent = 0 if parent is None else len(parent.locals)

    def define_variable(self, vname, type, is_attr=False):
        vinfo = VariableInfo(vname, type, is_attr)
        self.locals.append(vinfo)
        return vinfo

    def create_child_scope(self):
        child_scope = Scope(self)
        self.children.append(child_scope)
        return child_scope

    def is_defined(self, vname):
        return self.get_variable_info(vname) is not None

    def get_variable_info(self, vname):
        current = self
        top = len(self.locals)
        while current is not None:
            vinfo = Scope.find_variable_info(vname, current, top)
            if vinfo is not None:
                return vinfo
            top = current.index_at_parent
            current = current.parent
        return None

    def is_local(self, vname):
        return self.get_local_variable_info(vname) is not None

    def get_local_variable_info(self, vname):
        return Scope.find_variable_info(vname, self)

    @staticmethod
    def find_variable_info(vname, scope, top=None):
        if top is None:
            top = len(scope.locals)
        candidates = (vinfo for vinfo in itl.islice(scope.locals, top) if vinfo.var_name == vname)
        return next(candidates, None)

class VariableInfo:
    def __init__(self, var_name, type_name=None, is_attr=False):
        self.var_name = var_name
        self.type_name = type_name
        self.is_attr = is_attr

        #cil
        local_vinfo = None

        #code_gen
        self.offset = None

class ClassInfo:
    def __init__(self,class_name,ancestor=OBJECT):
        self.class_name=class_name
        self.ancestor=ancestor
        self.siblings=[]
        self.height=0
        self.methods={}
        self.attrs={}

        self.constructor = None

        #code_gen
        self.size = None


class MethodInfo:
    def __init__(self,method_name,signature):
        self.original_name = method_name
        self.method_name = method_name
        self.signature = signature

        #code_gen
        self.vtable_offset = None

class Error:
    def __init__(self,line,column,type,info):
        self.line = line
        self.column = column
        self.type = type
        self.info = info
    def __str__(self):
        return f"({self.line},{self.column}) {self.type}: {self.info}"