#!/usr/bin/env python3
"""
Main entry point for BLS automation script.
"""

from utils.browser import setup_selenium
from utils.network import send_reboot_request
from models.appointment import automate_process
import requests
import time


def run_automation_with_restart():
    """Runs automation, switches Wi-Fi if 403/429/520 occurs, and reboots modem if needed."""
    attempt = 0  
    driver = None
    
    while True:
        attempt += 1
        driver = None  # Reset driver to None at start of each attempt
        
        try:
            print(f"🚀 Starting Automation Attempt {attempt}")

            driver = setup_selenium("")
            
            # Check if driver setup failed
            if driver is None:
                print("❌ Failed to setup Chrome driver. Retrying...")
                time.sleep(5)  # Wait before retrying
                continue
                
            success, status_code = automate_process(driver, "")
            
            if success:
                print("✅ Automation completed successfully! Exiting...")
                if driver:
                    driver.quit()
                break  

            elif status_code in [403, 429, 520]:
                print(f"⚠ {status_code} error detected! Restarting network and browser...")
                send_reboot_request(driver=driver)
                if driver:
                    driver.quit()
                continue

            else:
                print("⚠ Unknown error occurred. Retrying...")
                if driver:
                    driver.quit()
                continue

        except requests.exceptions.ConnectionError as e:
            print(f"⚠ API Connection Error: {e}")
            print(f"🔄 Retrying in 10 seconds...")
            if driver:
                driver.quit()
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            if driver:
                driver.quit()
            continue

    print("🚨 Automation process terminated.")


if __name__ == "__main__":
    run_automation_with_restart()