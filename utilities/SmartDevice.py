import asyncio
from kasa import Discover, Module
import logging

class SmartDevice:

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self.device_map = self._loop.run_until_complete(Discover.discover())

    def list_devices(self):
        return {ip: dev.alias for ip, dev in self.device_map.items()}

    def power_light(self, requested_status, light):
        self._loop.run_until_complete(self._power_light(requested_status, light))

    def light_exists(self, light):
        device_list = self.list_devices()
        if light in device_list:
            return True
        else:
            return False

    def light_status(self, light):
        return self._loop.run_until_complete(self._light_status(light))

    async def _light_status(self, light):
        if self.light_exists(light):
            light_obj = self.device_map[light]
            await light_obj.update()
            if light_obj.is_off:
                return f"{light} is off"
            else:
                return f"{light} is on"
        else:
            logging.error(f"{light} not found in discovered devices")

    def adjust_brightness(self, light, brightness):
        return self._loop.run_until_complete(self._adjust_brightness(light, brightness))

    def adjust_hue(self, light, hue, saturation, value):
        return self._loop.run_until_complete(self._adjust_hue(light, hue, saturation, value))

    async def _adjust_brightness(self, light, brightness):
        if self.light_exists(light):
            light_obj = self.device_map[light]
            await light_obj.update()
            light_module = light_obj.modules[Module.Light]
            await light_module.set_brightness(brightness)
            return f"Set brightness of {light} to {brightness}%"
        else:
            logging.error(f"{light} not found in discovered devices.")
            return f"{light} not found"

    async def _adjust_hue(self, light, hue, saturation, value):
        if self.light_exists(light):
            light_obj = self.device_map[light]
            await light_obj.update()
            light_module = light_obj.modules[Module.Light]
            await light_module.set_hsv(hue, saturation, value)
            return f"Set color of {light} to HSV({hue}, {saturation}, {value})"
        else:
            logging.error(f"{light} not found in discovered devices.")
            return f"{light} not found"

    async def _power_light(self, requested_status, light):
        if self.light_exists(light):
            light_obj = self.device_map[light]
            await light_obj.update()
            if requested_status == "on" and light_obj.is_off:
                await light_obj.turn_on()
                logging.info(f"{light} was turned on")
            elif requested_status == "off" and light_obj.is_on:
                await light_obj.turn_off()
                logging.info(f"{light} was turned off")
            else:
                logging.info(f"{light} already in requested state!")
        else:
            logging.error(f"{light} not found in discovered devices")

    def blink_effect(self, light, seconds):
        return self._loop.run_until_complete(self._blink_effect(light, seconds))

    async def _blink_effect(self, light, seconds):
        if self.light_exists(light):
            light_obj = self.device_map[light]
            await light_obj.update()
            for _ in range(seconds):
                await light_obj.turn_on()
                await asyncio.sleep(0.5)
                await light_obj.turn_off()
                await asyncio.sleep(0.5)
            return f"Blinked {light} for {seconds} seconds"
        else:
            logging.error(f"{light} not found in discovered devices")
            return f"{light} not found"