import os

from sqlalchemy import create_engine, ForeignKey, func
from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker

Base = declarative_base()

class Series( Base ):
    __tablename__ = 'series'
    item = Column( String )
    tag = Column( String, primary_key=True )
    title = Column( String )
    imdb = Column(String)
    
    episodes = relationship( 'Episode', backref='episodes' )

class Episode( Base ):
    __tablename__ = 'episode'
    tag = Column( String, primary_key=True )
    title = Column( String )
    path = Column( String )
    series = Column( String, ForeignKey( 'series.tag' ) )
    season = Column( Integer )

class Movie( Base ):
    __tablename__ = 'movie'
    id = Column( Integer, primary_key=True )
    title = Column( String )
    path = Column( String )
    imdb = Column( String )