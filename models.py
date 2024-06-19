from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    sender = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
