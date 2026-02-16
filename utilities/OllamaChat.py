import os
import logging
from datetime import datetime
import requests

logging.basicConfig(level=logging.DEBUG)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_devices",
            "description": "List all discovered smart devices on the network. Returns a dict of IP addresses mapped to device names.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_devices",
            "description": "Fuzzy search for smart devices by name or IP address. Use this to resolve a user's description (like 'bedroom lights') to actual device IPs before controlling them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term to match against device names or IPs (e.g. 'bedroom', 'living room')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "power_light",
            "description": "Turn a smart light on or off by its IP address. Always use search_devices first to resolve device names to IPs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "light": {
                        "type": "string",
                        "description": "The IP address of the light (e.g. '10.0.0.90')"
                    },
                    "requested_status": {
                        "type": "string",
                        "enum": ["on", "off"],
                        "description": "Whether to turn the light on or off"
                    }
                },
                "required": ["light", "requested_status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "light_status",
            "description": "Check whether a smart light is currently on or off. Use search_devices first to resolve device names to IPs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "light": {
                        "type": "string",
                        "description": "The IP address of the light (e.g. '10.0.0.90')"
                    }
                },
                "required": ["light"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_brightness",
            "description": "Set the brightness of a smart light. Use search_devices first to resolve device names to IPs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "light": {
                        "type": "string",
                        "description": "The IP address of the light (e.g. '10.0.0.90')"
                    },
                    "brightness": {
                        "type": "integer",
                        "description": "Brightness level from 0 to 100"
                    }
                },
                "required": ["light", "brightness"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_hue",
            "description": "Set the color of a smart light using HSV values. You must convert color names to HSV. Examples: 'red' = (0, 100, 100), 'light blue' = (200, 50, 100), 'warm white' = (30, 20, 100), 'purple' = (270, 100, 100), 'green' = (120, 100, 100). Use search_devices first to resolve device names to IPs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "light": {
                        "type": "string",
                        "description": "The IP address of the light (e.g. '10.0.0.90')"
                    },
                    "hue": {
                        "type": "integer",
                        "description": "Hue value from 0 to 360 (color wheel degree)"
                    },
                    "saturation": {
                        "type": "integer",
                        "description": "Saturation from 0 to 100 (0 = white, 100 = full color)"
                    },
                    "value": {
                        "type": "integer",
                        "description": "Value/brightness from 0 to 100"
                    }
                },
                "required": ["light", "hue", "saturation", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "blink_effect",
            "description": "Blink a smart light on and off repeatedly. The seconds parameter must be in seconds. Convert any time the user provides to seconds (e.g. '2 minutes' = 120, '30 seconds' = 30, '1 hour' = 3600). Use search_devices first to resolve device names to IPs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "light": {
                        "type": "string",
                        "description": "The IP address of the light (e.g. '10.0.0.90')"
                    },
                    "seconds": {
                        "type": "integer",
                        "description": "Duration in seconds to blink the light"
                    }
                },
                "required": ["light", "seconds"]
            }
        }
    }
]


class OllamaChat:

    SYSTEM_PROMPT = (
        "You are a smart home assistant called Mocha. You control smart lights and devices. "
        "When a user asks you to control a device, you MUST use your tools. "
        "Always use search_devices first to find matching device IPs, then use power_light or light_status for each IP returned. "
        "When the user asks about the status of lights (e.g. 'is the bedroom light on?', 'which lights are off?'), use search_devices or list_devices to get the IPs, then call light_status for each one. "
        "If the user mentions multiple rooms or groups (e.g. 'living room and bedroom'), call search_devices separately for each room, then power_light for every IP returned. "
        "If the user says 'all lights' or wants to control everything, use list_devices to get all devices, then use power_light for each one. "
        "If the user asks to turn on lights that are off (or turn off lights that are on), first get all device IPs, then call light_status for each to check their state, then call power_light only on the ones that need to change. "
        "When the user asks to change a light's color (e.g. 'make the bedroom lights light blue'), convert the color name to HSV values and use adjust_hue. "
        "When the user asks to change brightness (e.g. 'dim the bedroom lights'), use adjust_brightness with a value from 0-100. "
        "Never guess IP addresses. Never output raw JSON. Use the tool calling mechanism provided to you. "
        "When making tool calls, always include a brief acknowledgement message like 'Sure, turning off the bedroom lights now.' alongside your tool call."
    )

    def __init__(self, smart_device, fuzzy_matching, model="llama3.1", base_url=None):
        self.smart_device = smart_device
        self.fuzzy_matching = fuzzy_matching
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

    def greet(self):
        hour = datetime.now().hour
        if hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
        return self.chat(
            f"[SYSTEM] The user just opened the app. It is currently {time_of_day}. "
            f"Greet them with a brief, friendly message. Keep it to one sentence."
        )

    def _call_ollama(self, messages):
        response = requests.post(f"{self.base_url}/api/chat", json={
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "stream": False
        })
        response.raise_for_status()
        return response.json()["message"]

    def _execute_tool(self, name, args):
        if name == "list_devices":
            devices = self.smart_device.list_devices()
            return str(devices)

        elif name == "search_devices":
            results = self.fuzzy_matching.fuzzy_search(args["query"])
            if not results:
                return "No matching devices found."
            device_list = self.smart_device.list_devices()
            matched = {ip: device_list.get(ip, "Unknown") for ip in results}
            return str(matched)

        elif name == "power_light":
            self.smart_device.power_light(args["requested_status"], args["light"])
            return f"Turned {args['requested_status']} light at {args['light']}"

        elif name == "light_status":
            return self.smart_device.light_status(args["light"])

        elif name == "adjust_brightness":
            return self.smart_device.adjust_brightness(args["light"], args["brightness"])

        elif name == "adjust_hue":
            return self.smart_device.adjust_hue(args["light"], args["hue"], args["saturation"], args["value"])

        elif name == "blink_effect":
            return self.smart_device.blink_effect(args["light"], args["seconds"])

        return f"Unknown tool: {name}"

    def chat(self, user_message, on_status=None):
        self.messages.append({"role": "user", "content": user_message})
        response = self._call_ollama(self.messages)

        # Loop until the model stops calling tools
        while response.get("tool_calls"):
            # Show intermediate text (e.g. "Sure, turning off the lights now.")
            if response.get("content") and on_status:
                on_status(response["content"])

            self.messages.append(response)

            for tool_call in response["tool_calls"]:
                name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
                logging.debug(f"Tool call: {name}, args: {args}")
                result = self._execute_tool(name, args)
                self.messages.append({"role": "tool", "content": result})

            response = self._call_ollama(self.messages)

        self.messages.append(response)
        return response["content"]
