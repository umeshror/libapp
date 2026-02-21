from app.db.session import engine
from sqlalchemy import MetaData, Table

metadata = MetaData()
borrow_record = Table('borrow_record', metadata, autoload_with=engine)
for idx in borrow_record.indexes:
    print(idx.name, [c.name for c in idx.columns])
