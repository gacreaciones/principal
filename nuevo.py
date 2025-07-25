import bcrypt

password = "jhosmar1967".encode('utf-8')
hashed_password = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))

print(hashed_password.decode('utf-8'))