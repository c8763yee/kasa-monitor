import datetime
import os

from db_models import (
    HS300,
    PC,
    NintendoSwitch,
    PhoneCharge,
    RaspberryPi,
    Screen2K,
    ScreenFHD,
    engine,
)
from dotenv import load_dotenv
from paho.mqtt import client as mqtt
from sqlmodel import Session, SQLModel

load_dotenv(override=True)
tz_delta = datetime.timedelta(hours=0)
tz = datetime.timezone(tz_delta)


def now():
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


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
def on_connect(
    client: mqtt.Client, userdata: dict, flags: dict, reason_code: int, properties: dict
):
    print(f"=============== {'Connect':^15} ===============")
    client.subscribe("hs300/emeter/#")
    SQLModel.metadata.create_all(engine)


@mqttc.message_callback()
def on_message(client: mqtt.Client, userdata: dict, message: mqtt.MQTTMessage):
    table = TOPIC_MAPPING[message.topic]
    with Session(engine) as session:
        emeter = table.model_validate_json(message.payload.decode("utf-8"))
        session.add(emeter)

        session.commit()
        session.refresh(emeter)


if __name__ == "__main__":
    mqttc.connect(os.getenv("MQTT_HOST"))
    mqttc.loop_forever()
