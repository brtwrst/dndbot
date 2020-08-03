# pylint: disable=E0402, E0211, E1101
from .core import DBError, BaseDB, BaseModel, CharacterData
from .user_model import UserDB


class CharacterDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=Character)
        self.UserDB = UserDB(client)

    def query_active_char(self, user_id):
        user = self.UserDB.query_one(id=user_id)
        if not user.active_char:
            return None
        character = self.query_one(id=user.active_char)
        if not character:
            user.active_char = None

        return character

    def create_new(self, user_id, name, display_name, picture_url, npc_status, rank=None, level=None):
        user = self.UserDB.query_one(id=user_id)

        with self.client.state.get_session() as session:
            if session.query(CharacterData).filter_by(user_id=user_id, name=name).count() > 0:
                raise DBError(f'Character "{name}" already exists for user {user_id}')

        data = CharacterData(
            user_id=user.id,
            name=name,
            display_name=display_name,
            picture_url=picture_url,
            npc_status=npc_status,
            rank=rank,
            level=level,
        )

        with self.client.state.get_session() as session:
            session.add(data)

        return self.model_class(self.client, data)


class Character(BaseModel):
    table_type = CharacterData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def user_id(self):
        return self.data.user_id

    @user_id.setter
    def user_id(self, value):
        self.data.user_id = int(value)
        self.save_to_db()

    @property
    def name(self):
        return self.data.name

    @name.setter
    def name(self, value):
        self.data.name = str(value)
        self.save_to_db()

    @property
    def display_name(self):
        return self.data.display_name

    @display_name.setter
    def display_name(self, value):
        self.data.display_name = str(value)
        self.save_to_db()

    @property
    def picture_url(self):
        return self.data.picture_url

    @picture_url.setter
    def picture_url(self, value):
        self.data.picture_url = str(value)
        self.save_to_db()

    @property
    def npc_status(self):
        return self.data.npc_status

    @npc_status.setter
    def npc_status(self, value):
        self.data.npc_status = bool(value)
        self.save_to_db()

    @property
    def rank(self):
        return self.data.rank

    @rank.setter
    def rank(self, value):
        self.data.rank = value
        self.save_to_db()

    @property
    def level(self):
        return self.data.level

    @level.setter
    def level(self, value):
        self.data.level = value
        self.save_to_db()
