import json, os, sys

for name in ("endpoints.json", "services.json"):
    env_key = name.replace(".", "_").upper()
    value = os.environ.get(env_key)
    if value:
        with open(name, "w") as f:
            f.write(value)

os.execvp(sys.argv[1], sys.argv[1:])
