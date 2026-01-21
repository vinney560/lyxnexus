import re
def confirm_msg(msg):
    msgg = re.sub(r'\W', '', msg)[:10]
    z = re.match(r'^[A-Z0-9]+$', msgg)
    if not z:
        print("Found")
        return None
    print(msgg)

confirm_msg("1234567A9 0heheh")