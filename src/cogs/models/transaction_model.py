# pylint: disable=E0402, E0211, E1101
from .core import DBError, BaseDB, BaseModel, TransactionData


class TransactionDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=Character)

    def create_new(self, date, user_id, receiver_id, sender_id, description=None, confirmed=0, platinum=None, electrum=None, gold=None, silver=None, copper=None):
        data = TransactionData(
            date=date,
            user_id=user_id,
            receiver_id=receiver_id,
            sender_id=sender_id,
            description=description,
            confirmed=confirmed,
            platinum=platinum,
            electrum=electrum,
            gold=gold,
            silver=silver,
            copper=copper,
        )

        with self.client.state.get_session() as session:
            session.add(data)

        return self.model_class(self.client, data)


class Character(BaseModel):
    table_type = TransactionData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def date(self):
        return self.data.date

    @date.setter
    def date(self, value):
        self.data.date = str(value)
        self.save_to_db()

    @property
    def user_id(self):
        return self.data.user_id

    @user_id.setter
    def user_id(self, value):
        self.data.user_id = int(value)
        self.save_to_db()

    @property
    def receiver_id(self):
        return self.data.receiver_id

    @receiver_id.setter
    def receiver_id(self, value):
        self.data.receiver_id = int(value)
        self.save_to_db()

    @property
    def sender_id(self):
        return self.data.sender_id

    @sender_id.setter
    def sender_id(self, value):
        self.data.sender_id = int(value)
        self.save_to_db()

    @property
    def description(self):
        return self.data.description

    @description.setter
    def description(self, value):
        self.data.description = str(value)
        self.save_to_db()

    @property
    def confirmed(self):
        return self.data.confirmed

    @confirmed.setter
    def confirmed(self, value):
        self.data.confirmed = bool(value)
        self.save_to_db()

    @property
    def platinum(self):
        return self.data.platinum

    @platinum.setter
    def platinum(self, value):
        self.data.platinum = int(value)
        self.save_to_db()

    @property
    def electrum(self):
        return self.data.electrum

    @electrum.setter
    def electrum(self, value):
        self.data.electrum = int(value)
        self.save_to_db()

    @property
    def gold(self):
        return self.data.gold

    @gold.setter
    def gold(self, value):
        self.data.gold = int(value)
        self.save_to_db()

    @property
    def silver(self):
        return self.data.silver

    @silver.setter
    def silver(self, value):
        self.data.silver = int(value)
        self.save_to_db()

    @property
    def copper(self):
        return self.data.copper

    @copper.setter
    def copper(self, value):
        self.data.copper = int(value)
        self.save_to_db()
