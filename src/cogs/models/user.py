# pylint: disable=E0402, E0211, E1101
from .db_core import DBError, BaseDB, UserData

class UserDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=User)

    def create_new(self, _id, active_char=None):
        with self.client.state.get_session() as session:
            if session.query(UserData).filter_by(_id=_id).count() > 0:
                raise DBError(f'User {_id} already exists')

        user_data = UserData(
            _id=_id,
            active_char=active_char,
        )
        with self.client.state.get_session() as session:
            session.add(user_data)

        return self.model_class(self.client, user_data)

class User():
    table_type = 'UserData'

    def __init__(self, client, user_data):
        self.client = client
        self.data = user_data

    def save_to_db(self):
        with self.client.state.get_session() as session:
            session.add(self.data)

    @property
    def _id(self):
        return self.data._id

    @property
    def active_char(self):
        return self.data.active_char

    @active_char.setter
    def active_char(self, new):
        self.data.active_char = new
        self.save_to_db()
