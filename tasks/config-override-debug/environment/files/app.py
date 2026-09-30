import configparser
import glob
import json
import os
import sys

MAIN_CONFIG = "/app/config/app.ini"


def load_config():
    parser = configparser.ConfigParser()
    parser.read(MAIN_CONFIG)
    include_dir = parser.get("include", "dir", fallback=None)
    if include_dir:
        # Files in the include directory are read in name order; later files win.
        parser.read(sorted(glob.glob(os.path.join(include_dir, "*.ini"))))
    return {
        "host": parser.get("server", "host"),
        "port": parser.getint("server", "port"),
        "workers": parser.getint("server", "workers"),
        "log_level": parser.get("logging", "level"),
        "log_file": parser.get("logging", "file"),
    }


if __name__ == "__main__":
    config = load_config()
    if "--print-config" in sys.argv:
        print(json.dumps(config, indent=2, sort_keys=True))
    else:
        print(f"Listening on {config['host']}:{config['port']} with {config['workers']} workers")
