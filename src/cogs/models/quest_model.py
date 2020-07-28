# pylint: disable=E0402, E0211, E1101
import json
from .core import DBError, ModelError, BaseDB, BaseModel, QuestData
from .embed_model import EmbedDB


class QuestDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=Quest)

    def create_new(self, _id, date, multi, tier, rank_id, reward, title, description):
        with self.client.state.get_session() as session:
            if session.query(self.table_class).filter_by(_id=_id).count() > 0:
                raise DBError(f'Quest {_id} already exists')

        data = QuestData(
            _id=_id,
            embed_id=None,
            date=date,
            multi=multi,
            tier=tier,
            rank_id=rank_id,
            reward=reward,
            title=title,
            description=description,
            status=0,
        )

        with self.client.state.get_session() as session:
            session.add(data)

        return self.model_class(self.client, data)


class Quest(BaseModel):
    table_type = QuestData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statuses = {
            0: 'Offen',
            1: 'In Progress',
            2: 'Erfolgreich (Warte auf Bericht)',
            3: 'Erfolglos (Warte auf Bericht)',
            4: 'Abgeschlossen',
        }
        self.EmbedDB = EmbedDB(self.client)

    async def delete(self):
        with self.client.state.get_session() as session:
            status = session.query(type(self).table_type).filter_by(_id=self._id).delete()
        if status == 1:
            embed = self.EmbedDB.query_one(_id=self.embed_id)
            status = await embed.delete()
        return status

    @property
    def embed_id(self):
        return self.data.embed_id

    @embed_id.setter
    def embed_id(self, value):
        self.data.embed_id = int(value)
        self.save_to_db()

    @property
    def date(self):
        return self.data.date

    @date.setter
    def date(self, value):
        self.data.date = str(value)
        self.save_to_db()

    @property
    def multi(self):
        return self.data.multi

    @multi.setter
    def multi(self, value):
        self.data.multi = str(value)
        self.save_to_db()

    @property
    def tier(self):
        return self.data.tier

    @tier.setter
    def tier(self, value):
        self.data.tier = int(value)
        self.save_to_db()

    @property
    def rank_id(self):
        return self.data.rank_id

    @rank_id.setter
    def rank_id(self, value):
        self.data.rank_id = int(value)
        self.save_to_db()

    @property
    def reward(self):
        return self.data.reward

    @reward.setter
    def reward(self, value):
        self.data.reward = str(value)
        self.save_to_db()

    @property
    def title(self):
        return self.data.title

    @title.setter
    def title(self, value):
        self.data.title = str(value)
        self.save_to_db()

    @property
    def description(self):
        return self.data.description

    @description.setter
    def description(self, value):
        self.data.description = str(value)
        self.save_to_db()

    @property
    def status(self):
        return self.data.status

    @status.setter
    def status(self, value):
        self.data.status = int(value)
        self.save_to_db()

    async def edit(self, attribute, value):
        setattr(self, attribute, value)
        if not self.embed_id:
            return
        try:
            embed = self.EmbedDB.query_one(_id=self.embed_id)
            embed.content = self.create_embed_content()
            await embed.update()
        except ModelError:
            pass

    def create_embed_content(self):
        content_dict = {
            'title': self.title,
            'fields': [
                {
                    'name': 'Quest Nummer',
                    'value': f'{self._id}',
                    'inline': True
                },
                {
                    'name': 'Datum',
                    'value': f'{self.date}',
                    'inline': True
                },
                {
                    'name': 'Multi Session',
                    'value': f'{self.multi}',
                    'inline': True
                },
                {
                    'name': 'Tier',
                    'value': f'T{self.tier}',
                    'inline': True
                },
                {
                    'name': 'Rang',
                    'value': f'{self.client.mainguild.get_role(self.rank_id).mention}',
                    'inline': True
                },
                {
                    'name': 'Belohnung',
                    'value': f'{self.reward}',
                    'inline': True
                },
                {
                    'name': 'Beschreibung',
                    'value': f'{self.description}',
                    'inline': False
                }
            ],
            'author': {
                'name': f'Status: {self.statuses[self.status]}',
            }
        }

        return json.dumps(content_dict)
