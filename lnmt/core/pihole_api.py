import requests
import time
import logging
import json
from lnmt.config.loader import get_config

log_path = "/etc/lnmt/pihole_api_errors.log"
logging.basicConfig(filename=log_path, level=logging.WARNING, format="%(asctime)s %(levelname)s: %(message)s")

class PiHoleAPI:
    def __init__(self, url, api_key, test_mode=False, retries=3, retry_delay=2):
        self.url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.test_mode = test_mode
        self.retries = retries
        self.retry_delay = retry_delay

    def _request_with_retry(self, method, url, **kwargs):
        for attempt in range(self.retries):
            try:
                if method == "get":
                    response = requests.get(url, headers=self.headers, **kwargs)
                elif method == "post":
                    response = requests.post(url, headers=self.headers, **kwargs)
                elif method == "delete":
                    response = requests.delete(url, headers=self.headers, **kwargs)
                else:
                    raise ValueError("Unsupported HTTP method")
                response.raise_for_status()
                return response
            except Exception as e:
                logging.warning(f"Attempt {attempt+1} failed: {e}")
                time.sleep(self.retry_delay)
        raise RuntimeError(f"Pi-hole API error after {self.retries} attempts")

    def list_records(self):
        if self.test_mode:
            return [{"id": "test-1", "name": "test.local", "ip": "127.0.0.1", "group": "test"}]
        response = self._request_with_retry("get", f"{self.url}/dns/records/local")
        return response.json()

    def add_or_update_record(self, name, ip, group="default"):
        if self.test_mode:
            logging.info(f"[TEST MODE] Would add/update: {name} -> {ip} [{group}]")
            return {"name": name, "ip": ip, "group": group}
        data = {"name": name, "ip": ip, "group": group}
        response = self._request_with_retry("post", f"{self.url}/dns/records/local", json=data)
        return response.json()

    def delete_record(self, record_id):
        if self.test_mode:
            logging.info(f"[TEST MODE] Would delete record ID: {record_id}")
            return True
        response = self._request_with_retry("delete", f"{self.url}/dns/records/local/{record_id}")
        return response.status_code == 200

    def export_records(self, path):
        records = self.list_records()
        with open(path, "w") as f:
            json.dump(records, f, indent=2)
        return path

    def import_records(self, path):
        with open(path, "r") as f:
            records = json.load(f)
        for rec in records:
            self.add_or_update_record(rec["name"], rec["ip"], rec.get("group", "default"))
