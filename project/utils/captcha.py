"""
CAPTCHA solving logic.
"""

import base64
import io
import time
import requests
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import concurrent.futures

from config import API_KEY, NOCAPTCHA_API_URL


def extract_target_number(driver):
    """
    Extracts the target number from '.box-label' elements.
    If a number appears twice, return that number.

    :param driver: Selenium WebDriver instance.
    :return: The duplicated number if found, otherwise None.
    """
    try:
        try:
            pass
        except TimeoutException:
            print("❌ Iframe not found, cannot switch!")
            return None

        try:
            box_labels = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "box-label"))
            )
        except TimeoutException:
            print("❌ .box-label elements not found inside the iframe!")
            return None

        print(f"✅ Found {len(box_labels)} .box-label elements!")

        number_counts = defaultdict(int)

        def process_element(div):
            """ Extracts numbers from a .box-label element. """
            try:
                text = div.get_attribute("textContent").strip()  
                import re
                match = re.search(r"\b(\d+)\b", text)
                if match:
                    number = match.group(1)
                    number_counts[number] += 1
            except NoSuchElementException:
                print("⚠️ Element disappeared, skipping.")
            except Exception as e:
                print(f"⚠️ Error processing .box-label: {e}")

        with ThreadPoolExecutor(max_workers=45) as executor:
            executor.map(process_element, box_labels)

        for number, count in number_counts.items():
            if count == 2:
                print(f"✅ Found duplicated target number: {number}")
                driver.switch_to.default_content()
                return int(number)

        print("❌ No duplicated target number found.")
        driver.switch_to.default_content()
        return None

    except Exception as e:
        print(f"⚠️ Exception in extract_target_number: {e}")
        driver.switch_to.default_content()
        return None


def is_element_truly_visible(driver, element):
    """
    Translates the 'isElementTrulyVisible' logic from show.js to Python:
      1. Check CSS visibility: display != 'none', visibility != 'hidden', opacity != '0'
      2. Check offsetWidth/offsetHeight > 0
      3. Check bounding rect is within viewport
      4. Check elementFromPoint(...) to ensure it's not covered by another element
    """

    style = driver.execute_script(
        r"""
        var el = arguments[0];
        var st = window.getComputedStyle(el);
        return {
            display: st.display,
            visibility: st.visibility,
            opacity: st.opacity,
            width: el.offsetWidth,
            height: el.offsetHeight
        };
        """,
        element
    )

    if style["display"] == "none":
        return False
    if style["visibility"] == "hidden":
        return False
    if style["opacity"] == "0":
        return False
    if style["width"] == 0 or style["height"] == 0:
        return False

    rect = driver.execute_script(
        """
        var rect = arguments[0].getBoundingClientRect();
        return {
            top: rect.top, left: rect.left,
            bottom: rect.bottom, right: rect.right,
            width: rect.width, height: rect.height
        };
        """,
        element
    )
    viewport_width = driver.execute_script("return window.innerWidth;")
    viewport_height = driver.execute_script("return window.innerHeight;")

    in_viewport = (
        rect["width"] > 0 and rect["height"] > 0 and
        0 <= rect["top"] and 0 <= rect["left"] and
        rect["bottom"] <= viewport_height and rect["right"] <= viewport_width
    )
    if not in_viewport:
        return False

    center_x = rect["left"] + rect["width"] / 2
    center_y = rect["top"] + rect["height"] / 2

    top_element = driver.execute_script(
        "return document.elementFromPoint(arguments[0], arguments[1]);",
        center_x, center_y
    )
    if not top_element:
        return False

    if top_element._id == element._id:
        return True  

    descendants = element.find_elements(By.XPATH, ".//*")
    if top_element in descendants:
        return True

    return False


def find_visible_images_showjs_style(driver, max_images=9, max_duration=10):
    """
    Optimized version of show.js-like observation:
    - Detects images inside the correct iframe.
    - Ensures images & their parent divs are visible.
    - Stops at max_images or after max_duration seconds.
    - Uses WebDriverWait instead of constant looping.
    - Uses threading for maximum speed.
    """
    found = []
    found_b64 = set()
    start_time = time.time()

    print("🚀 Starting optimized scanning...")

    while time.time() - start_time < max_duration:
        try:
            divs_with_images = driver.find_elements(By.XPATH, "//div[img]")  
            
            def process_div(d):
                """ Process an image inside a div without scrolling. """
                try:
                    img = d.find_element(By.TAG_NAME, "img")  
                    src = img.get_attribute("src") or ""
                    if "/assets/images/logo.png" in src or "base64," not in src:
                        return

                    if is_element_truly_visible(driver, d) and is_element_truly_visible(driver, img):
                        base64_data = src.split("base64,", 1)[-1]
                        if base64_data not in found_b64:
                            found_b64.add(base64_data)
                            found.append((img, base64_data, d))
                            print(f"🖼 Found image: {base64_data[:50]}...")

                except Exception as e:
                    print(f"⚠️ Error processing image: {e}")

            with ThreadPoolExecutor(max_workers=45) as executor:
                executor.map(process_div, divs_with_images)

            if len(found) >= max_images:
                print("✅ Found enough images, stopping early.")
                return found

            WebDriverWait(driver, 1).until(lambda d: True)  

        except Exception as e:
            print(f"⚠️ Exception in image scanning: {e}")

    print("⏳ Finished scanning within time limit.")
    driver.switch_to.default_content()  
    return found


def click_correct_images(driver, visible_images, recognized_texts, target_number):
    """
    Clicks images that match the target number using multithreading.

    :param driver: Selenium WebDriver instance
    :param visible_images: List of tuples [(img_element, base64_string, parent_div)]
    :param recognized_texts: List of recognized numbers from NoCaptchaAI
    :param target_number: The correct number that needs to be selected
    """
    def click_image(index, parent_div, recognized_text):
        if int(recognized_text) == int(target_number):
            print(f"✅ Clicking Correct Image {index+1} (Recognized: {recognized_text})")
            action = ActionChains(driver)
            action.move_to_element(parent_div).click().perform()

    with concurrent.futures.ThreadPoolExecutor(max_workers=45) as executor:
        futures = []
        for i, (img, base64_str, parent_div) in enumerate(visible_images):
            if i >= len(recognized_texts):
                break
            futures.append(executor.submit(click_image, i, parent_div, recognized_texts[i]))
        
        concurrent.futures.wait(futures)


def compress_image(base64_data, max_size=50, quality=20):
    """
    Compresses a base64 image by:
    - Converting to grayscale
    - Resizing (keeping aspect ratio)
    - Saving in high-compression JPEG
    - Targeting max size ~50KB
    """
    try:
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))

        image = image.convert("L")

        width, height = image.size
        image = image.resize((width // 2, height // 2), Image.LANCZOS)

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality)
        compressed_data = base64.b64encode(output.getvalue()).decode("utf-8")

        return compressed_data
    except Exception as e:
        print(f"⚠ Error compressing image: {e}")
        return base64_data


def solve_captcha_batch(images_base64, driver=None, max_retries=3):
    """
    Solves a batch of CAPTCHAs using NoCaptchaAI.
    Sends 5 images in one thread and 4 images in another for speed.
    """

    total_images = len(images_base64)
    if total_images < 9:
        print(f"⚠ Not enough images ({total_images}/9) found! Trying anyway...")

    raw_images_base64 = [encode_image_native(img) for img in images_base64]

    images_part1 = raw_images_base64[:5]
    images_part2 = raw_images_base64[5:]

    recognized_texts = []  

    def process_images(image_set):
        """ Function to send images and collect results in a separate thread. """
        results = send_images_to_api(image_set)
        return [txt for txt in results if txt.isdigit()]  

    for attempt in range(1, max_retries + 1):
        print(f"📤 Attempt {attempt}/{max_retries} - Sending CAPTCHA images to NoCaptchaAI...")

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(process_images, images_part1)
            future2 = executor.submit(process_images, images_part2)

            recognized_texts.extend(future1.result())
            recognized_texts.extend(future2.result())

        recognized_texts = [txt for txt in recognized_texts if txt.isdigit()]

        if recognized_texts:
            print(f"✅ Combined Captcha Recognized: {recognized_texts}")
            return recognized_texts  

        print("❌ CAPTCHA recognition failed! Retrying...")

    print("❌ CAPTCHA solving failed after multiple attempts.")
    return []


def encode_image_native(base64_data):
    """
    Encodes the image in base64 without any compression or modifications.
    """
    try:
        image_data = base64.b64decode(base64_data)
        return base64.b64encode(image_data).decode("utf-8")  
    except Exception as e:
        print(f"⚠ Error encoding image: {e}")
        return base64_data  


def send_images_to_api(images_base64):
    """
    Sends images to NoCaptchaAI **without compression**.
    """
    try:
        payload = {
            "clientKey": API_KEY,
            "task": {
                "type": "ImageToTextTask",
                "body": images_base64,  
                "phrase": False,
                "case": True,
                "numeric": 1,
                "math": False,
                "minLength": 3,
                "maxLength": 3,
                "score": 0.7,
                "comment": "Enter the number you see on the image"
            },
            "languagePool": "en"
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/10.3.1",
            "apikey": API_KEY
        }

        response = requests.post(NOCAPTCHA_API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "solution" in data and isinstance(data["solution"], dict):
            return data["solution"].get("text", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ API Request failed: {e}")

    return []


def maybe_handle_captcha(driver, max_retries=4):
    """
    Handles CAPTCHA solving, clicks images, and submits the form.
    If CAPTCHA fails or is still visible, refreshes the page instead of restarting from 0.
    If a 429 Too Many Requests or 403 error appears, restarts the network before retrying.
    """
    from utils.logging_utils import inject_modal
    from utils.network import send_reboot_request
    from utils.helpers import wait_for_page_to_load
    from utils.ui_interaction import fill_pwd_and_verify
    
    driver.execute_script("document.body.style.zoom='75%'")
    for attempt in range(1, max_retries + 1):
        driver.execute_script("document.body.style.zoom='75%'")
        try:
            print(f"🔄 Attempt {attempt}/{max_retries} to solve CAPTCHA")

            if "Application Temporarily" in driver.page_source  or "Too Many Requests" in driver.page_source or "403 Forbidden" in driver.page_source:
                print("❌ 429/403 Error detected! Restarting network and refreshing...")
                send_reboot_request(driver)
                inject_modal(driver,"ban ...  N3awdo .... ","red")
                wait_for_page_to_load(driver)
                continue  

            if "newcaptcha/logincaptcha" in driver.current_url:
                target_number = extract_target_number(driver)
                if target_number is None:
                    print("🚨 CAPTCHA Number Extraction Failed! Refreshing and retrying...")
                    inject_modal(driver,"No Captcha Ai m7bch y3rf les image capctha !","red")
                    driver.quit()
                    wait_for_page_to_load(driver)
                    continue  

                print(f"🎯 Target number: {target_number}")

                visible_images = find_visible_images_showjs_style(driver, max_images=9, max_duration=5)
                if not visible_images:
                    print("🚨 No visible images found! Refreshing page and retrying...")
                    inject_modal(driver,"No Captcha Ai m7bch y3rf les image capctha !","red")
                    driver.service.process.kill()
                    wait_for_page_to_load(driver)
                    continue  

                only_base64_list = [b64 for _, b64, _ in visible_images]

                recognized_texts = solve_captcha_batch(only_base64_list, driver)
                if not recognized_texts or not all(len(txt) == 3 for txt in recognized_texts):
                    print("❌ CAPTCHA recognition failed! Refreshing page and retrying...")
                    inject_modal(driver,"No Captcha Ai m7bch y3rf les image capctha !","red")
                    driver.service.process.kill()
                    wait_for_page_to_load(driver)
                    continue  

                clicked = click_correct_images(driver, visible_images, recognized_texts, target_number)

                print(f"✅ CAPTCHA clicked successfully on attempt {attempt}.")

                try:
                    old = driver.current_url
                    fill_pwd_and_verify(driver)
                    
                    from models.appointment import is_change_password_page, is_change_Appointment_page
                    if is_change_password_page(driver):
                        driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                        return True
                        break
                    if "Please select all boxes with number" in driver.page_source:
                        print("⚠ CAPTCHA form still visible! Refreshing page and retrying...")
                        driver.service.process.kill()
                        continue  

                except TimeoutException:
                    print("❌ CAPTCHA Submit button not found! Refreshing and retrying...")
                    driver.service.process.kill()
                    continue  
                    
            elif "Appointment/AppointmentCaptcha"  in driver.current_url:
                target_number = extract_target_number(driver)
                if target_number is None:
                    print("🚨 CAPTCHA Number Extraction Failed! Refreshing and retrying...")
                    driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                    maybe_handle_captcha(driver)
                    continue  

                print(f"🎯 Target number: {target_number}")

                visible_images = find_visible_images_showjs_style(driver, max_images=9, max_duration=5)
                if not visible_images:
                    print("🚨 No visible images found! Refreshing page and retrying...")
                    driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                    wait_for_page_to_load(driver)
                    maybe_handle_captcha(driver)
                    continue  

                only_base64_list = [b64 for _, b64, _ in visible_images]

                recognized_texts = solve_captcha_batch(only_base64_list, driver)
                if not recognized_texts or not all(len(txt) == 3 for txt in recognized_texts):
                    print("❌ CAPTCHA recognition failed! Refreshing page and retrying...")
                    driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                    wait_for_page_to_load(driver)
                    maybe_handle_captcha(driver)
                    continue  

                clicked = click_correct_images(driver, visible_images, recognized_texts, target_number)

                print(f"✅ CAPTCHA clicked successfully on attempt {attempt}.")

                try:
                    wait = WebDriverWait(driver, 10)
                    submit_button = wait.until(EC.element_to_be_clickable((By.ID, "btnVerify")))
                    
                    driver.execute_script("arguments[0].scrollIntoView();", submit_button)
                    time.sleep(0.3)  

                    submit_button.click()
                    
                    wait_for_page_to_load(driver)
                    
                    from models.appointment import is_change_Appointment_page
                    if is_change_Appointment_page(driver) or "Appointment Slot" in  driver.page_source:
                        return True,2
                        break

                except TimeoutException:
                    print("❌ CAPTCHA Submit button not found! Refreshing and retrying...")
                    driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                    wait_for_page_to_load(driver)
                    maybe_handle_captcha(driver)
                    continue  

            wait_for_page_to_load(driver)

        except Exception:
            if "Appointment/AppointmentCaptcha"  in driver.current_url:
                driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                wait_for_page_to_load(driver)
                maybe_handle_captcha(driver)
                from models.appointment import click_visa
                click_visa(driver)
            print("handle captcha err")