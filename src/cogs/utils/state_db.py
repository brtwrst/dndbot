from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#pylint: disable=E1101
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    discord_id = Column(Integer, primary_key=True, autoincrement=False)
    active_char = Column(Integer, ForeignKey('characters.char_id'))

    def __repr__(self):
        return f'<User({self.discord_id=}, {self.active_char=})>'


class Character(Base):
    __tablename__ = 'characters'

    char_id = Column(Integer, primary_key=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.discord_id'), nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    picture_url = Column(String, nullable=False)
    npc_status = Column(Boolean, nullable=False)
    rank_override = Column(Integer)

    def __repr__(self):
        return f'<Character({self.char_id=}, {self.user_id=}, {self.name=}, {self.display_name=}, {self.picture_url=}, {self.npc_status=}, {self.rank_override=})>'


class State_DB():
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


