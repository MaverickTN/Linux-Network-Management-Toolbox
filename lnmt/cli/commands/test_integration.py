import sys
from lnmt.core import version, logger, notifier, health

def run_integration_test():
    print("[*] Running integration test...")
    try:
        health_status = health.run_health_check()
        latest_version = version.get_latest_version({})
        notifier.test_notify_all("Test message from integration script.")
        logger.log("integration", "Integration test completed.")
        print("[+] Integration test passed.")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Integration test failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    run_integration_test()
