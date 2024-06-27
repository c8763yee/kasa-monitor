import asyncio
import json
import logging
import os
import re
import threading
from typing import Optional

from kasa import SmartPlug, SmartStrip
from paho.mqtt import client as mqtt

from const import COMMAND_PATTERN, DEFAULT_PLUG_ID, SECOND, MINUTE
from loggers import setup_package_logger

logger = setup_package_logger(__name__, console_level=logging.INFO)

WAITING_TIME = 5 * SECOND
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


class HS300Command:
    toggle_mapping = {"on": "turn_on", "off": "turn_off"}

    def __init__(self, strip: SmartStrip) -> None:
        self.strip = strip

    async def turn_on(self, plug_id: int) -> None:
        """Turn on plug

        Args:
            plug_id (int): Child id
        """
        await self.strip.children[plug_id - 1].turn_on()

    async def turn_off(self, plug_id: int) -> None:
        """Turn off plug

        Args:
            plug_id (int): Child id
        """
        await self.strip.children[plug_id - 1].turn_off()

    async def toggle_plug(self, plug_id: int, status: Optional[str] = None) -> None:
        """Toggle plug status to turn on or off

        Args:
            plug_id (int): Child id
            status (Optional[bool], optional): Status to set. Defaults to None
                on: Turn on the plug
                off: Turn off the plug
                None: Toggle the plug status
        """
        assert (
            0 < plug_id <= len(self.strip.children)
        ), f"Invalid device id, must be between 1 and {len(self.strip.children)}"
        child: SmartPlug = self.strip.children[plug_id - 1]

        if not status or status not in self.toggle_mapping:
            status = "on" if not child.is_on else "off"
        await getattr(child, self.toggle_mapping[status])()


class HS300Controller:
    """A class to control the HS300 strip and its plugs
    Available commands:
        - toggle <plug_id>
        - turn_on <plug_id>
        - turn_off <plug_id>
    """

    update_required_commands = {}
    command_to_function_mapping = {
        **update_required_commands,
        "toggle": "toggle_plug",
        "on": "turn_on",
        "off": "turn_off",
    }

    async def execute_command(
        self,
        command: str,
        plug_id: int,
        update: Optional[bool] = False,
        payload: Optional[dict] = {},
    ) -> None:
        """
        Execute command on the strip or plug
        """
        assert command in self.command_to_function_mapping, "Invalid command"
        if update or command in self.update_required_commands:
            logger.info(f"Updating {command} {plug_id}")
            await self.commander.strip.update()

        command_function = getattr(
            self.commander, self.command_to_function_mapping[command]
        )
        await command_function(plug_id, **payload)

    def __init__(self) -> None:
        self.commander = HS300Command(HS300)


def publish_exceptions_to_mqtt(e: Exception) -> None:
    """Publish error to MQTT
    include:
        - exception: exception name and location of error
        - traceback
        - message

    Args:
        e (Exception): _description_
    """
    logger.exception(e)
    if mqttc.is_connected() is False:
        raise e
    mqttc.publish(
        "hs300/error",
        json.dumps(
            {
                "exception": f"{e.__class__.__name__} in {e.__traceback__.tb_frame.f_code.co_name}.{e.__traceback__.tb_lineno}",
                "traceback": str(e.__traceback__),
                "message": e.__str__(),
            }
        ),
        qos=0,
    )


def on_connect(client, userdata, flags, reason_code, properties):
    logger.info(f"Connected with result code {reason_code}")
    client.subscribe("hs300/command/#", 0)


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    # Since we subscribed only for a single channel, reason_code_list contains
    # a single entry
    if reason_code_list[0].is_failure:
        logger.warning(f"Broker rejected you subscription: {reason_code_list[0]}")
    else:
        logger.info(f"Broker granted the following QoS: {reason_code_list[0].value}")


async def handle_message(client, userdata, message):
    # received command for strip or plug
    # hs300/<command>/[<plug_id>]

    if (command_matches := re.match(COMMAND_PATTERN, message.topic)) is not None:
        if command_matches.lastindex == 2:
            command, plug_id = command_matches.groups()
            plug_id = int(plug_id)

        else:  # default to strip
            command = command_matches.group(1)
            plug_id = DEFAULT_PLUG_ID
        try:
            controller = HS300Controller()
            await controller.execute_command(
                command, plug_id, update=False, payload=json.loads(message.payload)
            )
        except Exception as e:
            publish_exceptions_to_mqtt(e)


def on_message(client, userdata, message):
    logger.info(
        f"Received message '{message.payload.decode()}' on topic '{message.topic}' with QoS {message.qos}"
    )

    asyncio.run_coroutine_threadsafe(handle_message(client, userdata, message), loop)


HS300 = SmartStrip("192.168.0.215")
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.connect(
    os.environ.get("MQTT_HOST", "localhost"),
    int(os.environ.get("MQTT_PORT", 1883)),
    keepalive=60,
)
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe


async def main():
    await HS300.update()
    strip_emeter = HS300.emeter_realtime
    mqttc.publish(
        "hs300/emeter",
        json.dumps(
            {
                "name": HS300.alias,
                "status": HS300.is_on,
                "V": strip_emeter.voltage,
                "W": strip_emeter.power,
                "A": strip_emeter.current,
                "total_wh": strip_emeter.total,
            }
        ),
        qos=0,
    )

    for i, child in enumerate(HS300.children, 1):
        child_emeter = child.emeter_realtime
        mqttc.publish(
            f"hs300/emeter/{i}",
            json.dumps(
                {
                    "name": child.alias,
                    "status": child.is_on,
                    "V": child_emeter.voltage,
                    "W": child_emeter.power,
                    "A": child_emeter.current,
                    "total_wh": child_emeter.total,
                }
            ),
            qos=0,
        )


def start_mqtt(loop):
    mqttc.loop_start()


if __name__ == "__main__":
    mqtt_thread = threading.Thread(target=start_mqtt, args=(loop,))
    mqtt_thread.start()

    async def inner_main():
        """Main loop to update emeter data and handle exceptions
        sleep for 58 seconds when an exception occurs
        sleep for 2 seconds after each iteration

        """
        while True:
            try:
                await main()
            except Exception as e:
                publish_exceptions_to_mqtt(e)
                await asyncio.sleep(1 * MINUTE - WAITING_TIME)
            finally:
                await asyncio.sleep(WAITING_TIME)

    try:
        loop.run_until_complete(inner_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting")
    except Exception as e:
        logger.error("An error occurred when running the main loop")
        publish_exceptions_to_mqtt(e)
    finally:
        mqttc.loop_stop()
        loop.close()
        mqtt_thread.join()
        logger.info("Exited")
