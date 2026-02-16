from utilities.SmartDevice import SmartDevice
from utilities.FuzzyMatching import FuzzyMatching
import os

devices = SmartDevice()
fuzzy_matching = FuzzyMatching()

available_devices = devices.list_devices()
fuzzy_matching.set_threshold(80)
fuzzy_matching.set_items(available_devices)


while True:
    [print(device) for device in available_devices.items()]
    user_input = input("Enter IP/Device Name: ")
    matching_values = fuzzy_matching.fuzzy_search(user_input)
    print(matching_values)

# while True:
#     cont = input("Type EXIT to Exit: ")
#     if cont == "EXIT":
#         break
#     print("Please select the light by IP you wish to turn off:")
#     for light in available_devices.items():
#         print(light)
#     light_selection = input("Enter IP/Device Name: ")
#     on_off = input("Enter on/off: ")
#     devices.power_light(requested_status=on_off, 
#                         light = light_ip)