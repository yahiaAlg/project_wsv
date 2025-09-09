"""
Appointment-related logic.
"""

import os
import json
import time
from itertools import cycle
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests

from config import cat
from utils.logging_utils import inject_modal, inject_js_model
from utils.helpers import wait_for_page_to_load, write_flag
from utils.captcha import maybe_handle_captcha
from utils.network import send_reboot_request, switch_interface
from utils.browser import restart_browser
from utils.ui_interaction import fill_email_and_verify, fill_pwd_and_verify, pick_category
from utils.email_utils import get_bls_consent_link, get_otp, send_email


l = cycle(["Normal", "Prime Time", "Premium"])


def is_change_password_page(driver):
    """
    Check if the '.AspNetCore.Cookies' cookie is set in Selenium WebDriver.

    :param driver: Selenium WebDriver instance.
    :return: True if the cookie is set, False otherwise.
    """
    return driver.get_cookie(".AspNetCore.Cookies") is not None


def is_change_Appointment_page(driver):
    """
    Checks if the current URL in Selenium driver contains
    'https://algeria.blsspainglobal.com/DZA/account/ChangePassword'.
    Returns True if it does, False otherwise.
    """
    target_substring = "https://algeria.blsspainglobal.com/DZA/Appointment/VisaType"
    current_url = driver.current_url
    return target_substring in current_url


def post_cookies_and_url(driver):
    api_url = "http://145.223.99.189:5000/api/store"
    headers = {"Content-Type": "application/json"}
    
    current_url = driver.current_url
    
    cookies = []
    for cookie in driver.get_cookies():
        formatted_cookie = {
            "domain": cookie.get("domain", ""),
            "name": cookie.get("name", ""),
            "value": cookie.get("value", ""),
            "path": cookie.get("path", "/"),
            "expiry": int(cookie["expiry"]) if "expiry" in cookie else None,
            "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False)
        }
        cookies.append(formatted_cookie)
    
    data = {
        "url": current_url,
        "cookies": cookies
    }
    
    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        response_json = response.json()
        short_url = response_json.get("short_url")
        if short_url:
            return f"http://145.223.99.189:5000{short_url}/sefie"
    
    return None


def load_cookies_to_browser(driver):
    write_flag(0)
    file_path="cookies_sess.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for cookie in data.get("cookies", []):
            driver.add_cookie(cookie)
    except FileNotFoundError:
        print("Cookies file not found.")


def get_bls_selfie_links(driver):
    js_script = r"""
    (function() {
        let foundLinks = [];

        function captureRequests() {
            const open = window.XMLHttpRequest.prototype.open;
            window.XMLHttpRequest.prototype.open = function(method, url) {
                if (url.includes("https://bls-selfie.com/Client.php")) {
                    foundLinks.push(url);
                }
                return open.apply(this, arguments);
            };

            const send = window.XMLHttpRequest.prototype.send;
            window.XMLHttpRequest.prototype.send = function() {
                this.addEventListener('readystatechange', function() {
                    if (this.readyState === 4 && this.responseText) {
                        const matches = this.responseText.match(/https:\/\/bls-selfie\.com\/Client\.php[^\s"']+/g);
                        if (matches) {
                            foundLinks.push(...matches);
                        }
                    }
                });
                return send.apply(this, arguments);
            };
        }

        function searchAllLinks() {
            let allLinks = document.querySelectorAll("a[href], iframe[src], script[src], link[href], img[src]");
            allLinks.forEach(link => {
                let url = link.href || link.src;
                if (url.includes("https://bls-selfie.com/Client.php")) {
                    foundLinks.push(url);
                }
            });
        }

        captureRequests();
        searchAllLinks();

        return [...new Set(foundLinks)];
    })();
    """
    xhr_override_script = r"""
    // Save original XMLHttpRequest send method
    const originalXhrSend = XMLHttpRequest.prototype.send;
    const originalXhrOpen = XMLHttpRequest.prototype.open;

    // Override XMLHttpRequest to log URLs and responses
    XMLHttpRequest.prototype.open = function(method, url) {
    this._url = url;  // Store the URL for later use
    return originalXhrOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function() {
    this.addEventListener('load', function() {
        // Log the URL
        console.log('XHR URL:', this._url);
        
        // Check content type and log response accordingly
        const contentType = this.getResponseHeader('Content-Type');
        if (contentType && contentType.includes('application/json')) {
        console.log('XHR Response (JSON):', JSON.parse(this.responseText));
        } else if (contentType && contentType.includes('text/html')) {
        console.log('XHR Response (HTML):', this.responseText);
        } else if (contentType && contentType.includes('text')) {
        console.log('XHR Response (Text):', this.responseText);
        } else {
        console.log('XHR Response:', this.responseText);
        }
    });
    return originalXhrSend.apply(this, arguments);
    };
    """

    driver.execute_script(xhr_override_script)
    time.sleep(25)
    logs = driver.get_log('browser')
    for log in logs:
        print(log['message'])
    return driver.execute_script(js_script)


def selfie(driver):
    write_flag(1)
    time.sleep(180)
    try: 
        if not driver:
            print("Failed to initialize driver!")
            return
        
        driver.execute_script("document.body.style.zoom='33%'")
        wait = WebDriverWait(driver, 10)

        time.sleep(2)

        driver.execute_script("""
            setTimeout(() => {
                let dismissButton = document.querySelector("button.btn.btn-primary[data-bs-dismiss='modal']");
                if (dismissButton) {
                    dismissButton.click();
                    dismissButton.dispatchEvent(new Event('click', { bubbles: true }));
                    console.log("✅ Clicked the 'I agree' button successfully!");
                } else {
                    console.log("⚠ 'I agree' button not found!");
                }
            }, 1000);
        """)

        time.sleep(2)

        file_input = wait.until(EC.presence_of_element_located((By.ID, "uploadfile-1")))

        driver.execute_script("arguments[0].classList.remove('d-none'); arguments[0].style.display = 'block';", file_input)

        file_path = os.path.abspath(r"/Users/oxxy/Desktop/14.jpeg")

        file_input.send_keys(file_path)
        time.sleep(2)
        driver.execute_script("""
            setTimeout(() => {
                let understoodButton = document.querySelector("button.btn.btn-primary[data-bs-dismiss='modal'][onclick*='OnPhotoAccepted']");
                if (understoodButton) {
                    understoodButton.click();
                    understoodButton.dispatchEvent(new Event('click', { bubbles: true }));
                    console.log("✅ Clicked the 'Understood' button successfully!");
                } else {
                    console.log("⚠ 'Understood' button not found!");
                }
            }, 1000);
        """)
        time.sleep(2)

        if file_input.get_attribute("value"):
            print("✅ File uploaded successfully!")
        else:
            print("❌ File upload failed!")
        email_code_field = wait.until(EC.presence_of_element_located((By.ID, "EmailCode")))
        driver.execute_script("""
            var el = arguments[0];
            el.removeAttribute('onpaste');
            el.removeAttribute('oncopy');
            el.removeAttribute('disabled');
            el.style.display = 'block';
            el.style.visibility = 'visible';
        """, email_code_field)

        time.sleep(1)
        otp = get_otp(
            email_account="blszedmas@pm.me",
            password="XwkKiEcFBt3-MZ6PT8XjVg",
            imap_server="127.0.0.1",
            imap_port=1143,
            subject_contains="BLS Visa Appointment - Email Verification",
            check_interval=3
        )
        time.sleep(1)
        driver.execute_script(f"""
            setTimeout(() => {{
                let emailCodeInput = document.querySelector("input
                if (emailCodeInput) {{
                    emailCodeInput.value = "{otp}";
                    emailCodeInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    console.log("✅ Filled 'EmailCode' input successfully!");
                }} else {{
                    console.log("⚠ 'EmailCode' input not found!");
                }}
            }}, 1000);
        """)
        time.sleep(2)
        js_code = """
        function openCalendarAndSelectDate(daysAhead) {
            // Step 1: Click the calendar icon to open the datepicker
            const calendarIcon = document.querySelector(".k-icon.k-i-calendar");
            if (!calendarIcon) {
                console.warn("Calendar icon not found!");
                return;
            }

            // Simulate a human-like delay before opening the calendar
            setTimeout(() => {
                calendarIcon.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
                calendarIcon.click();

                // Step 2: Wait for calendar to appear, then select the date
                setTimeout(() => {
                    // Find today's date
                    const todayCell = document.querySelector(".k-today.k-state-focused");

                    if (todayCell) {
                        let currentDate = parseInt(todayCell.innerText, 10);
                        let targetDate = currentDate + daysAhead;

                        // Find the target date element
                        let targetCell = document.querySelector(`a[data-value][title*="${targetDate}"]`);

                        if (targetCell) {
                            // Simulate hover and click like a human
                            targetCell.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
                            setTimeout(() => {
                                targetCell.click();
                            }, Math.random() * 500 + 300); // Random delay before clicking
                        } else {
                            console.warn("Target date not found in calendar.");
                        }
                    } else {
                        console.warn("Today's date not found in calendar.");
                    }
                }, Math.random() * 800 + 500); // Random delay for realistic feel

            }, Math.random() * 1000 + 500); // Initial delay to open calendar
        }

        // Call function to select a date 4 days ahead
        openCalendarAndSelectDate(4);
        """

        driver.execute_script(js_code)
        time.sleep(6)
        driver.execute_script("""
            setTimeout(() => {
                let applicantDiv = document.querySelector("div[id^='app-'].bls-applicant");
                if (applicantDiv) {
                    applicantDiv.click();
                    applicantDiv.dispatchEvent(new Event('click', { bubbles: true }));
                    console.log("✅ Clicked the applicant selection div successfully!");
                } else {
                    console.log("⚠ Applicant selection div not found!");
                }
            }, 1000);
        """)

        time.sleep(1)
        driver.execute_script("""
            setTimeout(() => {
                let submitButton = document.querySelector("button
                if (submitButton) {
                    submitButton.click();
                    submitButton.dispatchEvent(new Event('click', { bubbles: true }));
                    console.log("✅ Clicked the 'Submit' button successfully!");
                } else {
                    console.log("⚠ 'Submit' button not found!");
                }
            }, 1000);
        """)
        
        try:
            url = post_cookies_and_url(driver)
            print(url)
            send_email("slamat.oxx@gmail.com", "url", url)

            inject_js_model(driver=driver,message=url)
            form_action_url = driver.execute_script("return document.getElementById('liveness_form').action;")

            form_fields = driver.execute_script("""
                let form = document.getElementById("liveness_form");
                let formData = new FormData(form);
                let data = [];
                for (let [key, value] of formData.entries()) {
                    data.push({name: key, value: value});
                }
                return data;
            """)

            script = f"""
                let newTab = window.open('', '_blank');
                if (newTab) {{
                    let newForm = newTab.document.createElement('form');
                    newForm.method = 'post';
                    newForm.action = "{form_action_url}";
                    newForm.style.display = 'none';  // Hide form

                    // Add extracted form fields
                    {''.join([f'let input_{i} = newTab.document.createElement("input"); input_{i}.type = "hidden"; input_{i}.name = "{field["name"]}"; input_{i}.value = "{field["value"]}"; newForm.appendChild(input_{i});' for i, field in enumerate(form_fields)])}
                    
                    newTab.document.body.appendChild(newForm);
                    newForm.submit();  // Auto-submit form
                }} else {{
                    alert("Popup blocked! Please allow popups.");
                }}
            """

            driver.execute_script(script)
            driver.execute_script("""
                        setTimeout(() => {
                            let submitButton = document.querySelector("button
                            if (submitButton) {
                                submitButton.click();
                                submitButton.dispatchEvent(new Event('click', { bubbles: true }));
                                console.log("✅ Clicked the 'Submit' button successfully!");
                            } else {
                                console.log("⚠ 'Submit' button not found!");
                            }
                        }, 1000);
            """)
            print("Clicked the 'Accept' button.")
            time.sleep(30)
        except Exception as e:
            print("Error:", e)
            time.sleep(30)

    except Exception:
        time.sleep(200)
        print


def sa7(driver):
    write_flag(1)
    
    print("I'm in saaaaA777777")

    try:
        driver.execute_cdp_cmd("Debugger.disable", {})
        driver.execute_cdp_cmd("Debugger.setBreakpointsActive", {"active": False})
    except Exception as e:
        print(f"Error disabling debugger: {e}")

    wait_for_page_to_load(driver=driver)

    script = """
(async function () {
    console.log("🚀 Running optimized booking script...");

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function waitForElement(selector, timeout = 5000) {
        let startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            let element = document.querySelector(selector);
            if (element && element.offsetParent !== null) {
                return element;
            }
            await sleep(200);
        }
        console.log(`❌ Element '${selector}' not found within timeout.`);
        return null;
    }

    async function selectRandomDateAndCheckSlots() {
        console.log("🔄 Selecting a new random date...");

        let dateLabels = Array.from(document.querySelectorAll("label.form-label"))
            .filter(label => label.textContent.includes("Appointment Date"))
            .filter(label => {
                let element = label.closest("div");
                return element && window.getComputedStyle(element).display !== 'none';
            });

        if (dateLabels.length === 0) {
            console.log("❌ No visible labels found with 'Appointment Date'. Exiting script.");
            return false;
        }

        for (let label of dateLabels) {
            let calendarIcon = label.closest("div").querySelector(".k-icon.k-i-calendar");
            if (calendarIcon) {
                console.log("✏️ Clicking calendar icon...");
                calendarIcon.click();
                await sleep(200);
            }

            for (let i = 0; i < 3; i++) { // Retry up to 3 times
                let availableDates = [...document.querySelectorAll("td[role='gridcell'] a.k-link")]
                    .filter(dateLink => {
                        let parentCell = dateLink.closest("td[role='gridcell']");
                        return (
                            parentCell &&
                            !parentCell.classList.contains("k-state-disabled") &&
                            window.getComputedStyle(dateLink).display !== "none"
                        );
                    });

                if (availableDates.length > 0) {
                    let randomDate = availableDates[Math.floor(Math.random() * availableDates.length)];
                    let dateTitle = randomDate.getAttribute("title");
                    console.log("📅 Clicking random available date:", dateTitle);
                    randomDate.scrollIntoView({ behavior: "smooth", block: "center" });
                    await sleep(100);
                    randomDate.click();
                    await sleep(100);
                    return true;
                }

                console.log("⚠️ No valid dates found. Clicking next month to retry...");
                let nextMonthButton = document.querySelector(".k-icon.k-i-arrow-60-right");
                if (nextMonthButton) {
                    nextMonthButton.click();
                    await sleep(300);
                } else {
                    console.log("❌ Next month button not found. Stopping.");
                    return false;
                }
            }
        }

        return false;
    }

    async function expandSlotDropdown() {
        console.log("🔎 Searching for the correct dropdown container...");

        let dropdowns = [...document.querySelectorAll(".k-widget.k-dropdown")];

        let visibleDropdown = dropdowns.find(dropdown => {
            let rect = dropdown.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(dropdown).display !== "none";
        });

        if (!visibleDropdown) {
            console.log("❌ No visible dropdown found.");
            return false;
        }

        let dropdownButton = visibleDropdown.querySelector(".k-select");
        if (!dropdownButton) {
            console.log("❌ Could not find the dropdown button inside the visible dropdown.");
            return false;
        }

        console.log("🔽 Clicking dropdown button...");
        dropdownButton.click();
        await sleep(100);

        return true;
    }

    async function selectLastSuccessSlot() {
        console.log("🔎 Expanding slot selection dropdown...");
        let dropdownOpened = await expandSlotDropdown();
        if (!dropdownOpened) {
            console.log("❌ Could not expand slot dropdown. Exiting.");
            return false;
        }

        console.log("🔎 Checking available slots...");

        let slotsLoaded = await waitForElement("li.k-item .slot-item.bg-success", 5000);
        if (!slotsLoaded) {
            console.log("⏳ Slots did not load in time. Exiting.");
            return false;
        }

        let availableSlots = [...document.querySelectorAll("li.k-item")]
            .filter(li => li.querySelector(".slot-item.bg-success"));

        console.log(`📌 Found ${availableSlots.length} available slots with 'bg-success' class.`);

        if (availableSlots.length > 0) {
            let lastSlot = availableSlots[availableSlots.length - 1];

            console.log(`✅ Selecting last 'bg-success' slot: ${lastSlot.textContent.trim()}`);

            lastSlot.scrollIntoView({ behavior: "smooth", block: "center" });
            lastSlot.dispatchEvent(new Event("mouseenter", { bubbles: true }));
            await sleep(100);
            lastSlot.click();
            await sleep(600);

            console.log("✔️ Slot clicked! No more retries needed.");
            return true;
        } else {
            console.log("⚠️ No available slots with 'bg-success' found.");
            return false;
        }
    }

    async function clickSubmitButton() {
        let submitButton = await waitForElement("
        if (!submitButton) {
            console.log("❌ Submit button not found.");
            return false;
        }

        while (submitButton.disabled) {
            console.log("⏳ Waiting for submit button to be enabled...");
            await sleep(200);
        }

        console.log("🖱️ Clicking Submit button...");
        submitButton.scrollIntoView({ behavior: "smooth", block: "center" });
        await sleep(100);
        submitButton.click();
        console.log("✔️ Submit button clicked!");

        return true;
    }

    async function checkRedirectAfterSubmit() {
        console.log("⏳ Waiting for page redirection...");
        await sleep(4000); // Wait 4 seconds for potential redirection

        if (window.location.href.includes("/Appointment/ApplicantSelection")) {
            console.log("✅ Successfully redirected to the correct page.");
            return true;
        } else {
            console.log("❌ Page did not redirect. Retrying process from the beginning...");
            return false;
        }
    }

    async function main() {
        console.log("🎯 Running optimized booking script...");

        while (true) { // Keep retrying until successful redirection
            let dateSelected = await selectRandomDateAndCheckSlots();
            if (!dateSelected) {
                console.log("❌ No available dates found. Retrying...");
                continue; // Restart the process
            }
            await sleep(300);
            let slotSelected = await selectLastSuccessSlot();
            if (!slotSelected) {
                console.log("❌ No available slots found. Retrying...");
                continue; // Restart the process
            }

            console.log("🎯 Successfully selected date and slot.");
            let submitSuccess = await clickSubmitButton();

            if (submitSuccess) {
                let redirected = await checkRedirectAfterSubmit();
                if (redirected) {
                    console.log("🎉 Booking process completed successfully!");
                    return; // Stop the script on success
                }
            }

            console.log("🔄 Restarting booking process...");
            
        }
    }

    main();
})();

    """

    try:
        driver.execute_script(script)
        time.sleep(20)
    except Exception as e:
        print(f"Error executing script: {e}")

    wait_for_page_to_load(driver=driver)

    print("✅ Script execution completed.")
    if "Application Temporarily" in driver.page_source  or "Too Many Requests" in driver.page_source or "403 Forbidden" in driver.page_source:
        print("❌ 429/403 Error detected! Restarting network and refreshing...")
        send_reboot_request(driver)
        wait_for_page_to_load(driver)
        driver.quit()


def click_visa(driver):
    try:
        driver.execute_script("document.body.style.zoom='75%'")
        wait_for_page_to_load(driver)
        if "Please select all boxes with number" in driver.page_source:
            print("🔄 Solving CAPTCHA before clicking Submit...")
            captcha_solved = maybe_handle_captcha(driver)
            
            if not captcha_solved:
                print("❌ CAPTCHA solving failed! Refreshing and retrying...")
                driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                inject_modal(driver,"No Captcha Ai m7bch y3rf les image capctha !","red")
                maybe_handle_captcha(driver)
                click_visa(driver)
                wait_for_page_to_load(driver=driver)
                return  
        
            try:
                submit_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "btnVerify"))
                )
                
                print("✅ CAPTCHA solved! Clicking Submit button...")
                driver.execute_script("arguments[0].click();", submit_button)  
                wait_for_page_to_load(driver=driver)  
                
                if "Please select all boxes with number" in driver.page_source:
                    print("⚠ CAPTCHA form still visible! Clicking Submit again...")
                    inject_modal(driver,"No Captcha Ai m7bch y3rf les image capctha !","red")
                    driver.execute_script("arguments[0].click();", submit_button)
                    wait_for_page_to_load(driver=driver)
                return
            except TimeoutException:
                print("❌ Submit button not found! Refreshing and retrying...")
                driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                wait_for_page_to_load(driver=driver)
                click_visa(driver)
        
        wait_for_page_to_load(driver=driver)

        wait_for_page_to_load(driver)
        if "Application Temporarily" in driver.page_source  or "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Too Many Requests" in driver.page_source:
            print("❌ 403 Forbidden detected on APPOINTMENT page. Restarting network and browser...")
            send_reboot_request(driver)
            inject_modal(driver,"3tak b ban ... nzido n3awdo b des ip new !","red")
            
            from utils.network import restart_network_and_browser
            restart_network_and_browser(driver)
            return  

        driver.execute_script("""
        setTimeout(() => {
            let modal = document.querySelector('.modal.show');
            if (modal) {
                let modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) modalInstance.hide();
            }
            let acceptButton = document.querySelector('.modal-content .modal-footer .btn.btn-success');
            if (acceptButton) {
                acceptButton.click();
                console.log("Accepted after dismissing modal");
            } else {
                console.log("Accept button not found");
            }
        }, 1000);
        """)
        
        wait_for_page_to_load(driver=driver)  

        for label_text, selection, choice in [
            ("Category", pick_category, l),
            ("Location", "//li[@class='k-item' and normalize-space()='Algiers']", None),
            ("Visa Type", "//li[@class='k-item' and normalize-space()='Visa renewal / renouvellement de visa']", None)
        ]:

            labels = driver.find_elements(By.TAG_NAME, "label")
            for lbl in labels:
                if label_text in lbl.text.strip():
                    dropdown_span = lbl.find_element(By.XPATH, "following::span[@role='listbox']")
                    driver.execute_script("arguments[0].click();", dropdown_span)
                    wait_for_page_to_load(driver=driver)
                    if callable(selection):
                        selection(driver, choice)
                    else:
                        element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, selection)))
                        driver.execute_script("arguments[0].click();", element)

                    print(f"✅ Selected {label_text}")
                    wait_for_page_to_load(driver=driver)
                    if "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Application Temporarily" in driver.page_source:
                        print("❌ 403 Forbidden detected on APPOINTMENT page. Restarting network and browser...")

                        send_reboot_request(driver)
                        
                        driver.service.process.kill()
                        driver = restart_browser(driver)
                        continue  

        driver.execute_script("""
        setTimeout(() => {
            let modal = document.querySelector('.modal.show');
            if (modal) {
                let modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) modalInstance.hide();
            }
            let okButton = document.querySelector('.modal-content .modal-footer .btn.btn-primary');
            if (okButton) {
                okButton.click();
                console.log("✅ Clicked 'OK' button successfully!");
            } else {
                console.log("⚠ 'OK' button not found!");
            }
        }, 1000);
        """)
        
        wait_for_page_to_load(driver=driver)  

        time.sleep(0.3)
        labels = driver.find_elements(By.TAG_NAME, "label")
        for lbl in labels:
            if "Visa Sub Type" in lbl.text.strip():
                dropdown_span = lbl.find_element(By.XPATH, "following::span[@role='listbox']")
                driver.execute_script("arguments[0].click();", dropdown_span)
                wait_for_page_to_load(driver=driver)
                element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//li[@class='k-item' and normalize-space()='ALG 4']")))
                driver.execute_script("arguments[0].click();", element)
                print("✅ Selected Visa Sub Type")
                wait_for_page_to_load(driver=driver)
        
        submit_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "btnSubmit")))
        
        driver.execute_script("arguments[0].click();", submit_button)
        print("✅ Clicked 'Submit' button successfully!")
        wait_for_page_to_load(driver=driver)

        if "Please select all boxes with number" in driver.page_source:
            maybe_handle_captcha(driver=driver)
            if "Invalid captcha selection" in driver.page_source:
                maybe_handle_captcha(driver=driver)
                
        if "Appointment Slot" in  driver.page_source:
            sa7(driver=driver) 
            inject_modal(driver,"Njrbo N7kmo date","yellow")
            time.sleep(4)
            if "Dear Visa Applicant" in driver.page_source:
                inject_modal(driver,"7kmnaha ...","green")
                
                inject_modal(driver,"Osber mat9l9ch 180 second ban n evitiw l ban .","yellow")
                selfie(driver)
                
                wait_for_page_to_load(driver)
                time.sleep(333033)
                return
            else:
                driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                click_visa(driver)
        elif "Currently, no slots" in driver.page_source:
            driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
            print("❌ No Slot")
            click_visa(driver)
        elif "Application Temporarily" in driver.page_source  or  "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Too Many Requests" in driver.page_source:
            print("❌ 403 Forbidden detected on LOGIN page. Restarting network and browser...")

            send_reboot_request(driver=driver)
    except Exception as e: 
        print(e)
        load_cookies_to_browser(driver)
        driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
        click_visa(driver)


def restart_network_and_browser(driver):
    """
    Restarts network only when necessary and prevents unnecessary router reboots.
    """
    from utils.network import check_connection
    
    print("🔄 Restarting network and browser...")

    if not check_connection():
        print("❌ No internet detected. Rebooting the router...")
        send_reboot_request(driver)  
    else:
        print("✅ Internet is working. Switching proxy instead of rebooting.")

    driver.quit()
    driver = restart_browser(driver)
    from utils.ui_interaction import restart_login_from_email
    return restart_login_from_email(driver)


def automate_process(driver, proxy):
    """Handles the full automation process, with 403 recovery & CAPTCHA handling."""
    from config import current_index

    try:
        while True:  
            print("🌐 Navigating to login page...")

            driver.get("https://algeria.blsspainglobal.com/DZA/account/login")

            if "Application Temporarily" in driver.page_source or "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Too Many Requests" in driver.page_source:
                print("❌ 403 Forbidden detected on LOGIN page. Restarting network and browser...")

                send_reboot_request(driver=driver)
                switch_interface()
                continue  
        
            if not fill_email_and_verify(driver):
                return False, 0  

            solved = maybe_handle_captcha(driver)
           
            print("🔄 Navigating to the appointment page...")
            driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
            wait_for_page_to_load(driver)

            if "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Application Temporarily" in driver.page_source:
                print("❌ 403 Forbidden detected on APPOINTMENT page. Restarting network and browser...")

                send_reboot_request(driver=driver)
                switch_interface()
                driver.quit()
                driver = restart_browser(driver)
                continue  

            text_you_seek = "Please select all boxes with number"
            if "email and click the accept button to proceed further"  in driver.page_source:
                try:
                    print("🔄 Redirecting to consent link...")
                    link = get_bls_consent_link()
        
                    driver.get(link)
                    driver.get("https://algeria.blsspainglobal.com/")
                    wait_for_page_to_load(driver)
                                
                    if "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Application Temporarily" in driver.page_source:
                        print("❌ 403 Forbidden detected on APPOINTMENT page. Restarting network and browser...")

                        send_reboot_request(driver=driver)
                        switch_interface()
                        driver.quit()
                        driver = restart_browser(driver)
                        continue  
        
                    driver.get("https://algeria.blsspainglobal.com/DZA/appointment/newappointment")
                    wait_for_page_to_load(driver)
                    if "403 Forbidden" in driver.page_source or driver.title.lower() == "forbidden" or "Application Temporarily" in driver.page_source:
                        print("❌ 403 Forbidden detected on APPOINTMENT page. Restarting network and browser...")

                        send_reboot_request(driver=driver)
                        switch_interface()
                        driver.quit()
                        driver = restart_browser(driver)
                        continue  
                    if text_you_seek in driver.page_source:
                        print(f"✅ Found '{text_you_seek}' in page source!")
                        maybe_handle_captcha(driver)
                        wait_for_page_to_load(driver=driver)
                    if "Invalid captcha selection" in driver.page_source:
                        maybe_handle_captcha(driver=driver)

                    if text_you_seek in driver.page_source:
                        print(f"✅ Found '{text_you_seek}' in page source!")
                        maybe_handle_captcha(driver)
                        wait_for_page_to_load(driver=driver)
                    if "Invalid captcha selection" in driver.page_source:
                        maybe_handle_captcha(driver=driver)
                    sa7(driver=driver) 
                except Exception as e:
                    print(f"❌ Error clicking visa: {e}")
                    driver.quit()
                    return False, 0

            else:
                print("✅ Already on Visa Type Selection Page.")
                if text_you_seek in driver.page_source:
                    print(f"✅ Found '{text_you_seek}' in page source!")
                    maybe_handle_captcha(driver)
                    if "Invalid captcha selection" in driver.page_source:
                        maybe_handle_captcha(driver=driver)

                click_visa(driver)

        return True, 200  

    except WebDriverException as e:
        click_visa(driver)
        sa7(driver=driver)
        time.sleep(88888)

        if "no such window" in str(e).lower():
            driver.quit()
            driver = restart_browser(driver)