path = "/etc/postgresql/18/main/postgresql.conf"
with open(path, "r") as f:
    lines = f.readlines()
with open(path, "w") as f:
    for line in lines:
        if line.startswith("listen_addresses ="):
            f.write("listen_addresses = 'localhost,127.0.0.1'\n")
        else:
            f.write(line)
print("Updated listen_addresses successfully.")

