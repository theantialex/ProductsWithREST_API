from aiohttp.web_urldispatcher import View
from asyncpg import Pool

class BaseView(View):
    URL: str

    @property
    def pg(self) -> Pool:
        return self.request.app['pg']

    @classmethod
    def get_sql(self, query, dialect=None):
        return str(query.compile(compile_kwargs={"literal_binds": True}, dialect=dialect))
