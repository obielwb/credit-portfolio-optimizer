import os
import sys

import pytest

# Ensure the project `src` package is importable during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

from src.schema.database.base import Base
from src.utils.db.db_client import DBClient


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


@pytest.fixture()
def in_memory_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_dbclient_create_read_update_delete_and_queries(in_memory_session):
    db = DBClient(in_memory_session)

    # create
    item = Item(name="foo")
    created = db.create(item)
    assert created.id is not None

    # get_by_id
    got = db.get_by_id(Item, created.id)
    assert got.name == "foo"

    # get_all
    all_items = db.get_all(Item)
    assert len(all_items) == 1

    # find_by
    found = db.find_by(Item, name="foo")
    assert len(found) == 1

    # exists
    assert db.exists(Item, name="foo") is True

    # count
    assert db.count(Item) == 1

    # bulk_create
    rows = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    db.bulk_create(Item, rows)
    assert db.count(Item) == 4

    # paginate
    page = db.paginate(Item, page=2, page_size=2)
    assert len(page) == 2

    # delete
    db.delete(created)
    assert db.exists(Item, id=created.id) is False


def test_save_and_partial_update_by_id(in_memory_session):
    db = DBClient(in_memory_session)

    item = Item(name="initial")
    saved = db.save(item)
    assert saved.id is not None
    assert saved.name == "initial"

    # partial update by id
    rows = db.update_by_id(Item, saved.id, {"name": "updated"})
    assert rows == 1

    got = db.get_by_id(Item, saved.id)
    assert got.name == "updated"
