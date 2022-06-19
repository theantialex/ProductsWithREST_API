from aiohttp.web_urldispatcher import View
from asyncpg import Pool
from sqlalchemy.dialects import postgresql

class BaseView(View):
    URL: str

    @property
    def pg(self) -> Pool:
        return self.request.app['pg']

    @classmethod
    def get_sql(self, query):
        return str(query.compile(compile_kwargs={"literal_binds": True}, dialect=postgresql.dialect()))
