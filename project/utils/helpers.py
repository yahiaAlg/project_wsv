"""
Miscellaneous helper functions.
"""

import os
import time
import random
import pyautogui
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException


def delete_if_exists(filepath):
    """Delete the file if it exists."""
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"Deleted old file: {filepath}")


def wait_for_page_to_load(driver, timeout=60):
    """Waits for the page to fully load using document.readyState."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ Page fully loaded!")
        return True
    except TimeoutException:
        print("❌ Page did not fully load within timeout.")
        return False


def random_mouse_movements(duration=2, step=50):
    """
    Moves the mouse randomly across the screen for a given duration.
    
    :param duration: How long to move the mouse (seconds).
    :param step: Max step size per movement.
    """
    start_time = time.time()
    screen_width, screen_height = pyautogui.size()

    while time.time() - start_time < duration:
        x = random.randint(0, screen_width)
        y = random.randint(0, screen_height)

        pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.5))
        time.sleep(random.uniform(0.1, 0.5))  

    print("✅ Random mouse movements completed.")


def random_scrolling(driver, duration=5):
    """
    Scrolls the webpage randomly up and down for a given duration.
    
    :param driver: Selenium WebDriver instance.
    :param duration: How long to scroll (seconds).
    """
    start_time = time.time()
    action = ActionChains(driver)

    while time.time() - start_time < duration:
        scroll_amount = random.randint(-500, 500)  
        action.scroll_by_amount(0, scroll_amount).perform()
        time.sleep(random.uniform(0.5, 0.8))  

    print("✅ Random scrolling completed.")


def write_flag(value):
    file_path = "flag.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(value))