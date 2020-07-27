from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

#pylint: disable=E1101
Base = declarative_base()

class DBError(Exception):
    pass

class BaseDB():
    def __init__(self, client, model_class):
        self.client = client
        self.model_class = model_class
        self.table_class = globals().get(self.model_class.table_type, None)
        if not self.table_class:
            raise DBError('No Table Class found')

    def query_one(self, **query_kwargs):
        with self.client.state.get_session() as session:
            try:
                data = session.query(self.table_class).filter_by(**query_kwargs).one()
            except NoResultFound:
                return None

        return self.model_class(self.client, data)

    def query_all(self, **query_kwargs):
        with self.client.state.get_session() as session:
            try:
                data = session.query(self.table_class).filter_by(**query_kwargs).all()
            except NoResultFound:
                return None
        if len(data) == 0:
            return None
        elif len(data) == 0:
            return self.model_class(self.client, data[0])
        else:
            return tuple(self.model_class(self.client, d) for d in data)

    def create_new(self):
        pass


class UserData(Base):
    __tablename__ = 'users'

    _id = Column('id', Integer, primary_key=True, autoincrement=False)
    active_char = Column(Integer)

    # def __repr__(self):
    #     return f'<UserData({self._id=}, {self.active_char=})>'

class CharacterData(Base):
    __tablename__ = 'characters'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    picture_url = Column(String, nullable=False)
    npc_status = Column(Boolean, nullable=False)
    rank = Column(Integer)
    level = Column(Integer)

    # def __repr__(self):
    #     return f'<CharacterData({self._id=}, {self.user_id=}, {self.name=}, {self.display_name=}, {self.picture_url=}, {self.npc_status=}, {self.rank=})>'


class TransactionData(Base):
    __tablename__ = 'transactions'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    account_nr = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    date = Column(String, nullable=False)
    platinum = Column(Integer)
    electrum = Column(Integer)
    gold = Column(Integer)
    silver = Column(Integer)
    copper = Column(Integer)
    confirmed = Column(Boolean, nullable=False)

    # def __repr__(self):
    #     return f'<TransactionData({self._id=}, {self.user_id=}, {self.description=}, {self.date=}, {self.platinum=}, {self.electrum=}, {self.gold=}, {self.silver=}, {self.copper=})>'


class EmbedData(Base):
    __tablename__ = 'embeds'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    channel_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    date = Column(String, nullable=False)

    # def __repr__(self):
    #     return f'<EmbedData({self._id=}, {self.user_id=}, {self.channel_id=}, {self.message_id=}, {self.content=}, {self.date=})>'

class QuestData(Base):
    __tablename__ = 'quests'

    _id = Column('id', Integer, primary_key=True, autoincrement=False)
    embed_id = Column(Integer)
    date = Column(String, nullable=False)
    multi = Column(String, nullable=False)
    tier = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    reward = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(Integer, nullable=False)

    # def __repr__(self):
    #     return f'<QuestData({self._id=}, {self.date=}, {self.multi=}, {self.tier=}, {self.rank=}, {self.reward=}, {self.description=})>'


class QuestToCharacter(Base):
    __tablename__ = 'quest_to_character'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    quest_id = Column(Integer, nullable=False)
    character_id = Column(Integer, nullable=False)

    # def __repr__(self):
    #     return f'<QuestToCharacter({self._id=}, {self.quest_id=}, {self.character_id=})>'

class DBConnector():
    def __init__(self, db_path):
        self.engine = create_engine(db_path)
        self.session_maker = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        session = self.session_maker()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
