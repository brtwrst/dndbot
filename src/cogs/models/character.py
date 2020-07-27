# pylint: disable=E0402, E0211, E1101
from .db_core import DBError, BaseDB, CharacterData
from .user import UserDB

class CharacterDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=Character)

    def create_new(self, user_id, name, display_name, picture_url, npc_status, rank=None, level=None):
        user = UserDB.query_one(_id=user_id)

        with self.client.state.get_session() as session:
            if session.query(CharacterData).filter_by(user_id=user_id, name=name).count() > 0:
                raise DBError(f'Character "{name}" already exists for user {user_id}')

        character_data = CharacterData(
            user_id=user._id,
            name=name,
            display_name=display_name,
            picture_url=picture_url,
            npc_status=npc_status,
            rank=rank,
            level=level,
        )

        with self.client.state.get_session() as session:
            session.add(character_data)

        return self.model_class(self.client, character_data)

class Character():
    table_type = 'CharacterData'

    def __init__(self, client, character_data):
        self.client = client
        self.data = character_data

    def save_to_db(self):
        with self.client.state.get_session() as session:
            session.add(self.data)

    @property
    def _id(self):
        return self.data._id

    @property
    def user_id(self):
        return self.data.user_id

    @user_id.setter
    def user_id(self, new):
        self.data.user_id = new
        self.save_to_db()

    @property
    def name(self):
        return self.data.name

    @name.setter
    def name(self, new):
        self.data.name = new
        self.save_to_db()

    @property
    def display_name(self):
        return self.data.display_name

    @display_name.setter
    def display_name(self, new):
        self.data.display_name = new
        self.save_to_db()

    @property
    def picture_url(self):
        return self.data.picture_url

    @picture_url.setter
    def picture_url(self, new):
        self.data.picture_url = new
        self.save_to_db()

    @property
    def npc_status(self):
        return self.data.npc_status

    @npc_status.setter
    def npc_status(self, new):
        self.data.npc_status = new
        self.save_to_db()

    @property
    def rank(self):
        return self.data.rank

    @rank.setter
    def rank(self, new):
        self.data.rank = new
        self.save_to_db()

    @property
    def level(self):
        return self.data.level

    @level.setter
    def level(self, new):
        self.data.level = new
        self.save_to_db()

    def delete(self):
        with self.client.state.get_session() as session:
            status = session.query(CharacterData).filter_by(_id=self._id).delete()
        return status
