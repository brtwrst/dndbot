# pylint: disable=E0402, E0211, E1101
from sqlalchemy.orm.exc import NoResultFound
from .core import BaseDB, BaseModel, TransactionData


class TransactionDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=Transaction)

    def get_history_for_account(self, receiver_id, num=12, start=0):
        with self.client.state.get_session() as session:
            try:
                data = (
                    session.query(TransactionData)
                    .filter_by(receiver_id=receiver_id)
                    .order_by(TransactionData.id.desc())
                    .limit(num+start)
                    .all()[start:num+start]
                )
            except NoResultFound:
                return None
        if len(data) == 0:
            return None
        else:
            return tuple(self.model_class(self.client, d) for d in data)

    def create_new(self, date, user_id, receiver_id, sender_id, description=None, confirmed=0, platinum=None, electrum=None, gold=None, silver=None, copper=None, linked=None):
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
            linked=linked,
        )

        with self.client.state.get_session() as session:
            session.add(data)

        return self.model_class(self.client, data)


class Transaction(BaseModel):
    table_type = TransactionData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def delete(self):
        with self.client.state.get_session() as session:
            status = session.query(type(self).table_type).filter_by(id=self.id).delete()
            if status == 1:
                if self.linked:
                    status += session.query(type(self).table_type).filter_by(id=self.linked).delete()
        return status

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
        self.data.sender_id = value
        self.save_to_db()

    @property
    def description(self):
        return self.data.description

    @description.setter
    def description(self, value):
        self.data.description = value
        self.save_to_db()

    @property
    def confirmed(self):
        return self.data.confirmed

    @confirmed.setter
    def confirmed(self, value):
        self.data.confirmed = value
        self.save_to_db()

    @property
    def platinum(self):
        return self.data.platinum

    @platinum.setter
    def platinum(self, value):
        self.data.platinum = value
        self.save_to_db()

    @property
    def electrum(self):
        return self.data.electrum

    @electrum.setter
    def electrum(self, value):
        self.data.electrum = value
        self.save_to_db()

    @property
    def gold(self):
        return self.data.gold

    @gold.setter
    def gold(self, value):
        self.data.gold = value
        self.save_to_db()

    @property
    def silver(self):
        return self.data.silver

    @silver.setter
    def silver(self, value):
        self.data.silver = value
        self.save_to_db()

    @property
    def copper(self):
        return self.data.copper

    @copper.setter
    def copper(self, value):
        self.data.copper = value
        self.save_to_db()

    @property
    def linked(self):
        return self.data.linked

    @linked.setter
    def linked(self, value):
        self.data.linked = value
        self.save_to_db()
