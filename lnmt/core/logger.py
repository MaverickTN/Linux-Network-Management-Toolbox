import logging
import os

log_path = "/var/log/lnmt/lnmt.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def log(source, message):
    logging.info(f"{source}: {message}")
