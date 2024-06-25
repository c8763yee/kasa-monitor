import datetime
import os

from dotenv import load_dotenv
from sqlalchemy import TIMESTAMP, Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BaseTable(Base):
    __abstract__ = True
    __table_args__ = {"mysql_charset": "utf8mb4"}
    ID = Column(Integer, nullable=False, primary_key=True)
    create_time = Column(TIMESTAMP, nullable=False, default=datetime.datetime.now())


class Emeter(BaseTable):
    __abstract__ = True
    name = Column(String(255), nullable=False)
    is_on = Column(Boolean, nullable=False)
    voltage = Column(Float(3, 3), nullable=False)
    current = Column(Float(3, 3), nullable=False)
    power = Column(Float(3, 3), nullable=False)
    total_wh = Column(Float, nullable=False)


class HS300(Emeter):
    __tablename__ = "hs300"


class PC(Emeter):
    __tablename__ = "pc"


class ScreenFHD(Emeter):
    __tablename__ = "screen_fhd"


class Screen2K(Emeter):
    __tablename__ = "screen_2k"


class NintendoSwitch(Emeter):
    __tablename__ = "nintendo_switch"


class PhoneCharge(Emeter):
    __tablename__ = "phone"


class RaspberryPi(Emeter):
    __tablename__ = "pi"


if __name__ == "__main__":
    # Load env variable
    load_dotenv(override=True)
    engine = create_engine(os.environ.get("SQL_SERVER"), echo=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
