import os

LOG_PATH = "/etc/lnmt/notifications.log"

def show_latest(n=20):
    if not os.path.exists(LOG_PATH):
        print("No notification log found.")
        return
    with open(LOG_PATH) as f:
        lines = f.readlines()[-n:]
    for l in lines:
        print(l.strip())

if __name__ == "__main__":
    show_latest()
