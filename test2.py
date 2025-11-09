import time

class home_system:
    def __init__(self):
        pass
    def open_door(self, command):
        print(f'Your command: {command} is being executed')
        print("Opening door...")
        time.sleep(4.5)
        print("Door opened.")
    def close_door(self, command):
        print(f'Your command: {command} is being executed')
        print('Closing door...')
        time.sleep(4.5)
        print('Door closed.')

executor = home_system()
print('Welcome Chloe!')
while True:
    chloe_input = input("Enter command: ")
    if chloe_input.lower() == 'open door':
        command = chloe_input.upper()
        executor.open_door(command)
    elif chloe_input.lower() == 'close door':
        command = chloe_input.upper()
        executor.close_door(command)
    elif chloe_input == 'q':
        break
    else:
        print('Command not found! Use Command Guide for more commands.')