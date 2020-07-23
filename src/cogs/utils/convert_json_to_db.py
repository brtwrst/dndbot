from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager


@contextmanager
def session_manager(session_maker):
    """Provide a transactional scope around a series of operations."""
    session = session_maker()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


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


engine = create_engine('sqlite:///state.db.sqlite3')
Base.metadata.create_all(engine)
session_maker = sessionmaker(engine)

if __name__ == '__main__':
    import json
    with open('users.json') as userfile:
        user_json = json.load(userfile)
    users_to_add = []
    characters_to_add = []
    for discord_id, userdata in user_json.items():
        discord_id = int(discord_id)
        character_data = userdata['characters']
        for charname, chardata in character_data.items():
            picture_url = chardata['picture']
            npc_status = chardata['npc']
            display_name = chardata['displayname']
            rank_override = chardata.get('rank_override', None)
            characters_to_add.append(Character(
                user_id=discord_id,
                name=charname,
                display_name=display_name,
                picture_url=picture_url,
                npc_status=npc_status,
                rank_override=rank_override
            ))

        users_to_add.append(User(
            discord_id=discord_id,
            active_char=None
        ))
    with session_manager(session_maker) as session:
        session.add_all(users_to_add)
        session.add_all(characters_to_add)

    # Set Active Characters
    for discord_id, userdata in user_json.items():
        discord_id = int(discord_id)
        active_char = userdata['active']
        with session_manager(session_maker) as session:
            user=session.query(User).filter_by(discord_id=discord_id).first()
            char_id = session.query(Character.char_id).filter_by(name=active_char).first().char_id
            user.active_char = char_id
            session.add(user)

