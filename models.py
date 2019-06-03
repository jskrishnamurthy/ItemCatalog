from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship

Base = declarative_base()
class User(Base):
    __tablename__ = 'user'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250),nullable=True)
    picture = Column(String(250),nullable=True)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,
           'picture'      : self.picture,
       }

class Category(Base):
    __tablename__ = 'category'

    category_id = Column(Integer, primary_key = True)
    category_name =Column(String(80), nullable = False)    
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    #Add add a decorator property to serialize data from the database

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'category_id'         : self.category_id,
           'category_name'           : self.category_name,
       }

class CategoryItem(Base):
    __tablename__ = 'category_item'

    title =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    item_id = Column(Integer,ForeignKey('category.category_id'))
    category = relationship(Category, cascade="save-update, merge, delete")
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'title'         : self.title,
           'id'         : self.id,
           'description'         : self.description,           
       }

engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)