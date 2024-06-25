import datetime
import json
import os

from dotenv import load_dotenv
from paho.mqtt import client as mqtt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db_models import (
    HS300,
    PC,
    ScreenFHD,
    Screen2K,
    NintendoSwitch,
    PhoneCharge,
    RaspberryPi,
)
from data_models import EmeterModel

load_dotenv(override=True)
tz_delta = datetime.timedelta(hours=0)
tz = datetime.timezone(tz_delta)


def now():
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


engine = create_engine(os.getenv("SQL_SERVER"), echo=True)
Session = sessionmaker(bind=engine)

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

TOPIC_MAPPING = {
    "hs300/emeter": HS300,
    "hs300/emeter/1": PC,
    "hs300/emeter/2": ScreenFHD,
    "hs300/emeter/3": Screen2K,
    "hs300/emeter/4": NintendoSwitch,
    "hs300/emeter/5": PhoneCharge,
    "hs300/emeter/6": RaspberryPi,
}


@mqttc.connect_callback()
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"=============== {'Connect':^15} ===============")
    client.subscribe("hs300/emeter/#")


@mqttc.message_callback()
def on_message(client, userdata, message):
    data = json.loads(message.payload.decode("utf-8"))
    emeter = EmeterModel(**data)
    with Session.begin() as session:
        table = TOPIC_MAPPING[message.topic]
        session.add(
            table(
                name=emeter.name,
                is_on=emeter.is_on,
                voltage=emeter.V,
                current=emeter.A,
                power=emeter.W,
                total_wh=emeter.total_wh,
                create_time=now(),
            )
        )


if __name__ == "__main__":
    mqttc.connect(os.getenv("MQTT_HOST"))
    mqttc.loop_forever()
