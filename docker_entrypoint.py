import json, os, sys, subprocess

for name in ("endpoints.json", "services.json"):
    env_key = name.replace(".", "_").upper()
    value = os.environ.get(env_key)
    if value:
        with open(name, "w") as f:
            f.write(value)

subprocess.run(["alembic", "upgrade", "head"], check=True)

os.execvp(sys.argv[1], sys.argv[1:])
