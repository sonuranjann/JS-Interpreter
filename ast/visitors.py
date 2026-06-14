# Optional visitor base for AST traversal
class NodeVisitor:
    def visit(self, node):
        method = "visit_" + type(node).__name__
        return getattr(self, method, self.generic_visit)(node)
    def generic_visit(self, node):
        raise NotImplementedError(f"No visit_{type(node).__name__}")
