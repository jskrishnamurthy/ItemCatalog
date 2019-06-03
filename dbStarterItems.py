from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Category,User,CategoryItem,Base

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Jay Kris", email="jaykris@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

User2 = User(name="Test Smith", email="jaykris@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User2)
session.commit()

# New Category
category1 = Category(category_name="Cricket", user_id=1)
session.add(category1)
session.commit()

# New Category items
categoryItem1 = CategoryItem(user_id=1, title = "Cricket Bat", 
                        description = "specialised piece of equipment used by batsmen in the sport of cricket to hit the ball",
                        category = category1)
session.add(categoryItem1)
session.commit()

categoryItem1 = CategoryItem(user_id=1, title = "Cricket Ball", 
                        description = "specialised piece of equipment used by bowler in the sport of cricket for bowling and dismissing batsmen",
                        category = category1)
session.add(categoryItem1)
session.commit()

# New Category
category2 = Category(category_name="Soccer", user_id=2)
session.add(category2)
session.commit()

# New Category items
categoryItem2 = CategoryItem(user_id=2, title = "Soccer Ball", 
                        description = "A Ball used in the sport of association football",
                        category = category2)
session.add(categoryItem2)
session.commit()

print ("added Category items!")