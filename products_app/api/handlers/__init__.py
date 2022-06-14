from .delete import DeleteView
from .imports import ImportsView
from .node import NodeView
from .nodes import NodesView
from .sales import SalesView

HANDLERS = [
    DeleteView, ImportsView, NodeView, NodesView, SalesView
]
