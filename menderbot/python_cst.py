import sys
from typing import Optional
import dataclasses
from dataclasses import dataclass
import json
import libcst as cst
from libcst.metadata import PositionProvider, WhitespaceInclusivePositionProvider

KIND_FN = 'fn'
KIND_PARAM = 'param'
KIND_SIGNATURE = 'sig'

PROP_NAME = 'name'
PROP_TYPE = 'type'
PROP_RETURN_TYPE = 'return_type'
PROP_DEFAULT = 'default'

class DataClassJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if callable(getattr(o, "as_dict", None)):
            return o.as_dict()
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


@dataclass
class SourcePosition:
    line: int
    col: int

    def render(self):
        return f'{self.line}:{self.col}'


@dataclass
class SourceRange:
    start: SourcePosition
    end: SourcePosition

    def render(self):
        return f'{self.start.render()}-{self.end.render()}'


@dataclass
class AstNode:
    kind: str
    src_range: SourceRange
    props: dict[str, str]
    children: list["AstNode"]  # forward declaration
    text: Optional[str]

    def __init__(self, kind, src_range):
        self.kind = kind
        self.src_range = src_range
        self.props = {}
        self.children = []
        self.text = None

    def as_dict(self) -> dict:
        d = {
            'kind': self.kind,
            'range': self.src_range.render(),
        }
        if self.props:
            d['props'] = self.props
        if self.children:
            d['children'] = self.children
        if self.text:
            d['text'] = self.text
        return d

    def children_filtered(self, kind):
        return [child for child in self.children if child.kind == kind]


class FunctionCollector(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,WhitespaceInclusivePositionProvider,)
    def __init__(self, enclosing_module, copy_function_text=False):
        # stack for storing the canonical name of the current function
        super().__init__()
        self.stack: list[str] = []
        # store the annotations
        self.annotations: dict[
            tuple[str, ...],  # key: tuple of canonical class/function name
            tuple[cst.Parameters, Optional[cst.Annotation]],  # value: (params, returns)
        ] = {}
        self.enclosing_module = enclosing_module
        self.copy_function_text: bool = copy_function_text
        self.function_asts: list[AstNode] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        self.stack.append(node.name.value)
        return None

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self.stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        name = node.name.value
        self.stack.append(name)
        self.annotations[tuple(self.stack)] = (node.params, node.returns)
        src_range = self._src_range(node)
        signature_start = src_range.start


        return_text = ""
        fn_ast = AstNode(kind=KIND_FN, src_range=src_range)
        if node.returns:
            signature_end = self._src_range(node.returns).end
            return_type = self.enclosing_module.code_for_node(node.returns.annotation)
            return_text = " -> " + return_type
            fn_ast.props[PROP_RETURN_TYPE] = return_type
        else:
            # Include space and add 1 to get after the paren.
            signature_end = self._src_range(node.params, include_whitespace=True).end
            signature_end.col = signature_end.col + 1
        signature_range = SourceRange(signature_start, signature_end)
        qname = '.'.join(tuple(self.stack))

        fn_ast.props[PROP_NAME] = qname
        signature_ast = AstNode(kind=KIND_SIGNATURE, src_range=signature_range)
        param_text = self.enclosing_module.code_for_node(node.params)
        signature_ast.text = f'def {name}({param_text}){return_text}'
        fn_ast.children.append(signature_ast)
        if self.copy_function_text:
            fn_ast.text = self.enclosing_module.code_for_node(node)
        for param in node.params.params:
            signature_ast.children.append(self._param_node_to_ast(param))
        if isinstance(node.params.star_arg, cst.Param):
            signature_ast.children.append(self._param_node_to_ast(node.params.star_arg))
        for param in node.params.kwonly_params:
            signature_ast.children.append(self._param_node_to_ast(param))
        if node.params.star_kwarg:
            signature_ast.children.append(self._param_node_to_ast(node.params.star_kwarg))
        for param in node.params.posonly_params:
            signature_ast.children.append(self._param_node_to_ast(param))
        self.function_asts.append(fn_ast)
        # Skipping inner functions
        return (
            False
        )

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        self.stack.pop()

    def _src_range(self, node: cst.CSTNode, include_whitespace=False):
        if include_whitespace:
            cst_range = self.get_metadata(cst.metadata.WhitespaceInclusivePositionProvider, node)
        else:
            cst_range = self.get_metadata(cst.metadata.PositionProvider, node)
        return SourceRange(
            start=SourcePosition(line=cst_range.start.line, col=cst_range.start.column + 1),
            end=SourcePosition(line=cst_range.end.line, col=cst_range.end.column + 1))

    def _param_node_to_ast(self, param_node: cst.Param) -> AstNode:
        param_range = self._src_range(param_node)
        param_name: str = param_node.name.value
        annotation = param_node.annotation
        ast = AstNode(kind=KIND_PARAM, src_range=param_range)
        if annotation:
            ast.props[PROP_TYPE] = self.enclosing_module.code_for_node(annotation.annotation)
        ast.props[PROP_NAME] = param_name
        if param_node.default:
            ast.props[PROP_DEFAULT] = self.enclosing_module.code_for_node(param_node.default)
        return ast

    # def visit_Name(self, node: cst.Name) -> None:
    #     # Only print out names that are parameters
    #     if self.get_metadata(IsParamProvider, node):
    #         pos = self.get_metadata(PositionProvider, node).start
    #         print(f"{node.value} found at line {pos.line}, column {pos.column}")


def collect_function_asts(code: str):
    module = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(module)
    visitor = FunctionCollector(module, copy_function_text=True)
    wrapper.visit(visitor)
    return visitor.function_asts


def to_json(o):
    return json.dumps(o, cls=DataClassJsonEncoder, indent=2)


def _main():
    print("Reading", sys.argv[0])
    with open(sys.argv[0], 'r') as file:
        code = file.read()
    for ast in collect_function_asts(code):
        print(to_json(ast))


if __name__ == "__main__":
    _main()
