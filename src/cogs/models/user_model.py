# pylint: disable=E0402, E0211, E1101
from sqlalchemy.orm.exc import NoResultFound
from .core import DBError, BaseDB, BaseModel, UserData


class UserDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=User)

    def query_one(self, **query_kwargs):
        with self.client.state.get_session() as session:
            try:
                data = session.query(self.table_class).filter_by(**query_kwargs).one()
            except NoResultFound:
                return self.create_new(query_kwargs['_id'])

        return self.model_class(self.client, data)

    def create_new(self, _id, active_char=None):
        with self.client.state.get_session() as session:
            if session.query(UserData).filter_by(_id=_id).count() > 0:
                raise DBError(f'User {_id} already exists')

        data = UserData(
            _id=_id,
            active_char=active_char,
        )
        with self.client.state.get_session() as session:
            session.add(data)

        return self.model_class(self.client, data)


class User(BaseModel):
    table_type = UserData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def active_char(self):
        return self.data.active_char

    @active_char.setter
    def active_char(self, value):
        self.data.active_char = int(value)
        self.save_to_db()
