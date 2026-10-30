with open("/etc/postgresql/18/main/postgresql.conf", "a") as f:
    f.write("\nlisten_addresses = '*'\n")
print("Configured listen_addresses = *")

