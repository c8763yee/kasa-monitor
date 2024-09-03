import datetime
import os

from dotenv import load_dotenv
from sqlmodel import Field, SQLModel, create_engine


class BaseTable(SQLModel):
    __abstract__ = True
    __table_args__ = {"mysql_charset": "utf8mb4", "extend_existing": True}
    ID: int | None = Field(default=None, primary_key=True)
    create_time: datetime.datetime = Field(default=datetime.datetime.now())


class Emeter(BaseTable):
    __abstract__ = True
    name: str = Field(nullable=False)
    status: bool = Field(nullable=False)
    voltage: float = Field(nullable=False, alias="V")
    current: float = Field(nullable=False, alias="A")
    power: float = Field(nullable=False, alias="W")
    total_wh: float = Field(nullable=False)


class HS300(Emeter, table=True):
    __tablename__ = "hs300"


class PC(Emeter, table=True):
    __tablename__ = "pc"


class ScreenFHD(Emeter, table=True):
    __tablename__ = "screen_fhd"


class Screen2K(Emeter, table=True):
    __tablename__ = "screen_2k"


class NintendoSwitch(Emeter, table=True):
    __tablename__ = "switch"


class PhoneCharge(Emeter, table=True):
    __tablename__ = "phone"


class RaspberryPi(Emeter, table=True):
    __tablename__ = "pi"


load_dotenv(override=True)
engine = create_engine(os.environ.get("SQL_SERVER"), echo=True)
if __name__ == "__main__":
    # Load env variable
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
