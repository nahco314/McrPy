import inspect
import ast
from types import FunctionType
from copy import deepcopy

class Macro:
    def set(self, code):
        self.ast = ast.parse(code).body[0]
        self.name = self.ast.name
        self.args = []
        self.name_to_idx = {}
        self.kwonlyargs = []

        try:
            self.posonryargs = set(map(lambda arg: arg.arg, self.ast.args.posonryargs))
        except AttributeError:
            self.posonryargs = set()
        try:
            self.vararg = self.ast.args.vararg.arg
        except AttributeError:
            self.vararg = None
        try:
            self.kwarg = self.ast.args.kwarg.arg
        except AttributeError:
            self.kwarg = None

        args, defaults, kwonlyargs, kw_defaults = \
            self.ast.args.posonlyargs + self.ast.args.args, \
            self.ast.args.defaults, self.ast.args.kwonlyargs, self.ast.args.kw_defaults

        for i in range(len(args)):
            self.args += [args[i].arg]
            self.name_to_idx[args[i].arg] = i

        for i in range(len(defaults)):
            self.args[i + len(args) - len(defaults)] = \
                (self.args[i + len(args) - len(defaults)], defaults[i].value)

        for i in range(len(kwonlyargs)):
            self.kwonlyargs += [kwonlyargs[i].arg]
            self.kw_name_to_idx[kwonlyargs[i].arg] = i

        for i in range(len(kw_defaults)):
            if kw_defaults[i]:
                self.kwonlyargs[i + len(kwonlyargs) - len(kw_defaults)] = \
                    (self.kwonlyargs[i + len(kwonlyargs) - len(kw_defaults)],
                     kw_defaults[i].value)

    def make_ast(self, mode):
        if mode == "Expr":
            return deepcopy(self.ast.body[0].value)

    def match(self, name):
        if self.name == name:
            return self
        return False

    def __or__(self, other):
        macros = Macros(self)
        return macros | other

    def __ior__(self, other):
        return self | other


class Macros:
    def __init__(self, first_macro):
        self.macros = [first_macro]

    def __or__(self, other):
        result = deepcopy(self)
        result.macros += [other]
        return result

    def __ior__(self, other):
        return self | other

    def match(self, name):
        for i in self.macros:
            if i.match(name):
                return i
        return False


class MacroSideAdapter(ast.NodeTransformer):
    def __init__(self, Macro, args, kwargs):
        var_map = {}
        kw_var_map = {}
        vararg = ast.List()
        kwarg = ast.Dict([], [])
        for i in Macro.args:
            if type(i) == tuple:
                var_map[i[0]] = i[1]
            else:
                var_map[i] = None

        for i in Macro.kwonlyargs:
            if type(i) == tuple:
                kw_var_map[i[0]] = i[1]
            else:
                kw_var_map[i] = None

        for i in range(len(args)):
            if i >= len(Macro.args):
                vararg.elts += [args[i]]
            var_map[Macro.args[i]] = args[i]

        for i in range(len(kwargs)):
            if kwargs[i][0] in kw_var_map:
                kw_var_map[kwargs[i][0]] = kwargs[i][1]
            elif kwargs[i][0] in var_map and kwargs[i][0] not in Macro.posonryargs:
                var_map[kwargs[i][0]] = kwargs[i][1]
            else:
                kwarg.keys += [kwargs[i][0]]
                kwarg.values += [kwargs[i][1]]

        self.var_map, self.kw_var_map, self.vararg, self.kwarg = \
            var_map, kw_var_map, vararg, kwarg


    def visit_Name(self, node: Name) -> Any:
        if node.id in self.var_map:
            new_node = deepcopy(self.var_map[node.id])
            new_node.ctx = node.ctx
            return new_node
        return node

    def visit_NamedExpr(self, node: NamedExpr) -> Any:
        self.generic_visit(node)
        return node


class MacroAdapter(ast.NodeTransformer):
    def __init__(self, Macro):
        self.Macro = Macro

    def visit_Call(self, node: Call) -> Any:
        name = node.func.id
        match_macro = self.Macro.match(name)
        if match_macro:
            call_kwargs = node.keywords
            kwargs = []

            for i in call_kwargs:
                kwargs += [(i.arg, i.value)]

            result = MacroSideAdapter(match_macro, node.args, kwargs)\
                .visit(match_macro.make_ast("Expr"))

            return result

        self.generic_visit(node)
        return node


def def_macro(func: function, mode="Expr") -> Macro:
    macro_obj = Macro()
    macro_obj.set(inspect.getsource(func))
    return macro_obj


def macro(macro_obj, *, print_code=False):
    def macro_sub(func):
        func_ast = ast.parse("global adapted_func\n"+inspect.getsource(func))
        new_ast = MacroAdapter(macro_obj).visit(func_ast)

        new_ast.body[1].name = "adapted_func"
        new_decorator_list = []
        for i in new_ast.body[1].decorator_list:
            if i.func.id != "macro":
                new_decorator_list += [i]
        new_ast.body[1].decorator_list = new_decorator_list

        if print_code:
            return ast.unparse(new_ast)

        exec(compile(new_ast, "<string>", "exec"))

        return adapted_func

    return macro_sub
