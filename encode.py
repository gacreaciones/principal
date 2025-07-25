import base64

with open("serviceAccountKey.json", "rb") as key_file:
    encoded = base64.b64encode(key_file.read()).decode('utf-8')
    
with open("serviceAccountKey.base64", "w") as out_file:
    out_file.write(encoded)