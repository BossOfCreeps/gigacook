from os import environ

from sqlalchemy import delete, insert, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

async_session = AsyncSession


class Base(AsyncAttrs, DeclarativeBase):
    @classmethod
    def __get_pk(cls):
        return getattr(cls, inspect(cls).primary_key[0].name)

    @classmethod
    async def create(cls, **kwargs):
        async with async_session() as session:
            await session.execute(insert(cls).values(**kwargs))
            await session.commit()

    @classmethod
    async def read(cls, user):
        async with async_session() as session:
            return list(await session.scalars(select(cls).where(cls.user == user)))

    @classmethod
    async def update(cls, pk, **kwargs):
        async with async_session() as session:
            await session.execute(update(cls).where(cls.__get_pk() == pk).values(**kwargs))
            await session.commit()

    @classmethod
    async def delete(cls, pk):
        async with async_session() as session:
            await session.execute(delete(cls).where(cls.__get_pk() == pk))
            await session.commit()


class Stage(Base):
    __tablename__ = "stage"

    user: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    @classmethod
    async def set(cls, user: int, name: str):
        if await cls.read(user):
            await cls.update(user, name=name)
        else:
            await cls.create(user=user, name=name)


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[int]
    name: Mapped[str]


class Bookmark(Base):
    __tablename__ = "bookmark"

    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[int]
    text: Mapped[str]


def run_async_session() -> None:
    global async_session

    engine = create_async_engine(environ["DB_URL"], echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
