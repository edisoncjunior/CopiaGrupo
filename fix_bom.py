with open("main_local_web_log.py", "rb") as f:
    data = f.read()

if data.startswith(b'\xef\xbb\xbf'):
    data = data[3:]

with open("main_local_web_log.py", "wb") as f:
    f.write(data)

print("BOM removido com sucesso.")
