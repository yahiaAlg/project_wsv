"""
UI interactions (clicks, form filling).
"""

import time
import random
from itertools import cycle
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, WebDriverException
from config import EMAIL, PASSWORD
from utils.helpers import wait_for_page_to_load, random_scrolling


l = cycle(["Normal", "Prime Time", "Premium"])


def pick_category(driver, categories):
    try:
        for category in categories:
            global xmo
            if f'>{category}<' in driver.page_source:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, f"//li[@class='k-item' and normalize-space()='{category}']"))
                )
                driver.execute_script("arguments[0].click();", element)
                xmo = category
                return
    except Exception as e:
        print(f"❌ Could not pick category: {e}")
        driver.service.process.kill()


def fill_email_and_verify(driver):
    """
    Fills in the email field, clicks 'Verify', and restarts if no valid input is found.
    """
    
    random_scrolling(driver=driver, duration=random.randint(1, 1))

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @type='email']"))
        )
        
        input_fields = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email']")
        print(f"🖊 Found {len(input_fields)} input fields.")

        filled = False  

        for idx, field in enumerate(input_fields, start=1):
            try:
                wait_for_page_to_load(driver)

                if field.get_attribute("disabled"):
                    driver.execute_script("arguments[0].removeAttribute('disabled');", field)

                field.click()
                field.clear()
                field.send_keys(EMAIL)
                print(f"✅ Filled Input {idx} with {EMAIL}")
                filled = True  
                break  

            except ElementNotInteractableException:
                print(f"⚠ Input {idx} is not interactable. Skipping...")
                continue  

        if not filled:
            print("❌ No valid input fields found! Refreshing and retrying...")
            driver.service.process.kill()
            wait_for_page_to_load(driver=driver)
            return fill_email_and_verify(driver)  

        wait_for_page_to_load(driver=driver)
        time.sleep(0.4)
        
        verify_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Verify')]"))
        )
        driver.execute_script("arguments[0].click();", verify_button)
        print("✅ Clicked 'Verify' button.")

        wait_for_page_to_load(driver=driver)
        if "Invalid appointment request" in driver.page_source:
            print("❌ Invalid appointment request detected! Restarting from email input...")
            driver.service.process.kill()
            wait_for_page_to_load(driver=driver)
            return fill_email_and_verify(driver)  

        return True  

    except (TimeoutException, WebDriverException) as e:
        print(f"⚠ WebDriverException while filling email: {e}")
        return False


def fill_pwd_and_verify(driver):
    time.sleep(1)
    """
    Fills in the PASSWORD field, clicks 'Verify', and restarts if no valid input is found.
    Only fills the password if the URL contains 'newcaptcha' or 'logincaptcha'.
    """
    current_url = driver.current_url.lower()

    if "account/changepassword" in current_url:
        print("🔒 Change Password page detected! Skipping password entry.")
        return

    try:
        js_script = """
        const passwordContainers = document.querySelectorAll('div[class^="mb-"].position-relative');

        const isVisible = (element) => {
            if (!element) return false;
            const style = window.getComputedStyle(element);
            return (
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                style.opacity !== '0' &&
                element.offsetParent !== null
            );
        };

        const visiblePasswordContainers = Array.from(passwordContainers).filter(container => {
            const inputField = container.querySelector('input[type="password"]');
            return inputField && isVisible(container) && isVisible(inputField);
        });

        // Return the IDs of visible password input fields
        return visiblePasswordContainers.map(container => container.querySelector('input[type="password"]').id);
        """

        visible_password_ids = driver.execute_script(js_script)

        if visible_password_ids:
            password_field = driver.find_element(By.ID, visible_password_ids[0])
            password_field.send_keys(PASSWORD)  
        
        submit_button = driver.find_element(By.ID, "btnVerify")
    
        driver.execute_script("arguments[0].scrollIntoView();", submit_button)  
        
        submit_button.click()
        print("Submit button clicked successfully!")
        print("✅ Clicked 'Verify' button.")
        time.sleep(0.4)
        
        if "Invalid appointment request" in driver.page_source:
            print("❌ Invalid appointment request detected! Restarting from email input...")
            driver.quit()
            wait_for_page_to_load(driver=driver)
            return fill_email_and_verify(driver)  

        return True  
        time.sleep(12)
    except (TimeoutException, WebDriverException) as e:
        print(f"⚠ WebDriverException while filling password: {e}")
        return False


def pause():
    input("Press Enter to continue...")


def wait_for_overlay(driver):
    """Wait for any overlay to disappear."""
    try:
        WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CLASS_NAME, "global-overlay-loader")))
        print("Overlay is no longer present.")
    except TimeoutException:
        print("Timeout while waiting for overlay to disappear.")


def check_availability_and_retry(driver, cat):
    from models.appointment import click_visa
    from utils.captcha import maybe_handle_captcha
    
    if "no slots are available" in driver.page_source:
        print("RESTARTINGxye")
        
        driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
        wait_for_page_to_load(driver)
        
        if any(msg in driver.page_source for msg in ["403 Forbidden", "Application Temporarily"]):
            print("❌ 403 Forbidden detected. Restarting network and browser...")
            from utils.network import send_reboot_request
            from utils.network import switch_interface
            send_reboot_request(driver)
            switch_interface()
            
            driver.service.process.kill()
            from utils.browser import restart_browser
            restart_browser(driver)
        wait_for_page_to_load(driver=driver)
        if "Please select all boxes with number" in driver.page_source:
            maybe_handle_captcha(driver)

            wait_for_page_to_load(driver=driver)
            if "Invalid captcha selection" in driver.page_source:
                maybe_handle_captcha(driver=driver)

        click_visa(driver)


def restart_login_from_email(driver):
    """
    If login fails due to missing password, restart from email input.
    """
    from models.appointment import load_cookies_to_browser
    from utils.captcha import maybe_handle_captcha
    
    print("🔄 Restarting login process from email input...")

    load_cookies_to_browser(driver)
    driver.get("https://algeria.blsspainglobal.com/DZA/account/login")
    wait_for_page_to_load(driver)

    if not fill_email_and_verify(driver):
        print("❌ Email verification failed again! Retrying...")
        driver.service.process.kill()
        wait_for_page_to_load(driver=driver)
        return False  

    captcha_solved = maybe_handle_captcha(driver)
    if not captcha_solved:
        print("❌ CAPTCHA solving failed again! Restarting from email input...")
        return False  

    fill_pwd_and_verify(driver)  

    print("✅ Login restarted successfully!")
    return True


def submit_captcha_if_needed(driver):
    """
    Submits the CAPTCHA form if necessary using JavaScript if needed.
    """
    try:
        submit_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "btnVerify"))
        )

        if submit_button.is_displayed() and submit_button.is_enabled():
            submit_button.click()
            print("✅ Clicked 'Submit' button.")
        else:
            print("⚠ 'Submit' button is not clickable! Using JavaScript instead.")
            driver.execute_script("arguments[0].click();", submit_button)

        time.sleep(0.5)  
    except Exception as e:
        print(f"⚠ 'Submit' button not found. Continuing anyway... {e}")