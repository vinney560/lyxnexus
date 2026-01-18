mobile = "0712345678"
phone = f"+254{mobile.strip()[1:] if mobile.startswith('0') else mobile.strip()}"
print(phone)  # Output: +254712345678