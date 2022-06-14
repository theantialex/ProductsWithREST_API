from .base import BaseView


class NodeView(BaseView):
    URL = r'/node/{id:\w+}/statistics'

    @property
    def id(self):
        return str(self.request.match_info.get('id'))