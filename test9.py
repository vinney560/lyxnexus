import random

def brute_force():
    try:
        count = 0
        _pin = int(input("Enter PIN to break: "))
        print("=" * 40)
        print("Attempting break sequence initiated....")
        print("=" * 40)
        while True:
            choice = random.choice(range(0000, 9999))
            if choice == _pin:
                print(f"PIN [{choice}] Found")
                print(f"Tried: {count} pins")
                break
            count += 1
    except KeyboardInterrupt:
        print("Exiting....")
    except ValueError:
        print("PIN must be numeric: ")

if __name__ == '__main__':
    brute_force()