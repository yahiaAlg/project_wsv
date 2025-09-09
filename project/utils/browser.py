"""
Browser setup, restart, and utilities.
"""

import os
import random
import shutil
import undetected_chromedriver as uc
from fake_useragent import UserAgent


def create_proxy_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    """
    Creates a persistent Chrome extension for proxy authentication.
    """
    extension_dir = os.path.join(os.getcwd(), "proxy_auth_extension")

    if os.path.exists(extension_dir):
        shutil.rmtree(extension_dir)
    os.makedirs(extension_dir, exist_ok=True)

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Auth Extension",
        "permissions": [
            "proxy",
            "tabs",
            "storage",
            "unlimitedStorage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version": "22.0.0"
    }
    """

    background_js = f"""
    chrome.proxy.settings.set(
        {{
            value: {{
                mode: "fixed_servers",
                rules: {{
                    singleProxy: {{
                        scheme: "http",
                        host: "{proxy_host}",
                        port: parseInt("{proxy_port}")
                    }},
                    bypassList: ["localhost", "127.0.0.1"]
                }}
            }},
            scope: "regular"
        }},
        function() {{}}
    );

    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    with open(os.path.join(extension_dir, "manifest.json"), "w") as f:
        f.write(manifest_json)

    with open(os.path.join(extension_dir, "background.js"), "w") as f:
        f.write(background_js)

    return extension_dir


def get_apple_mobile_user_agent():
    """Returns a random User-Agent for Apple devices (iPhone, iPad, Mac)."""
    ua = UserAgent()
    
    apple_user_agents = {
        "iPhone": ua.ios_safari,  
        "iPad": ua.ipad       
    }

    device, user_agent = random.choice(list(apple_user_agents.items()))
    return device, user_agent


def get_resolution(device):
    """Returns the correct screen resolution based on the selected Apple device."""
    resolutions = {
        "Mac": (2560, 1600),  
        "iPhone": (390, 844), 
        "iPad": (1180, 820)   
    }
    return resolutions.get(device, (1920, 1080))


def setup_selenium(x):
    try:
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")
        options.add_argument("--incognito")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--disable-background-networking")
        
        prefs = {
            "profile.default_content_setting_values.notifications": 1,  
            "profile.default_content_setting_values.popups": 1,  
            "profile.default_content_setting_values.geolocation": 1,  
            "profile.default_content_setting_values.media_stream_mic": 1,  
            "profile.default_content_setting_values.media_stream_camera": 1,  
            "profile.default_content_setting_values.automatic_downloads": 1,  
        }
        options.add_experimental_option("prefs", prefs)

        # Let undetected_chromedriver handle the driver path automatically
        # Remove the chrome_driver_path specification
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=None)

        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        driver.execute_script("""
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

        return driver
        
    except Exception as e:
        print(f"Failed to setup Chrome driver: {e}")
        return None


def is_driver_alive(driver):
    """Checks if the WebDriver session is still alive."""
    try:
        driver.current_url  
        return True
    except:
        return False


def restart_browser(driver):
    """Restarts the browser and returns a new WebDriver instance."""
    print("🔄 Restarting browser...")
    if driver and hasattr(driver, 'service') and driver.service.process:
        driver.service.process.kill()
    return setup_selenium("")


def is_element_interactable(driver, element):
    return element.is_displayed() and element.is_enabled()


def screenshot_entire_page(driver, filename=".//imgs//full_page.png"):
    """Takes a screenshot of the entire current browser view."""
    driver.save_screenshot(filename)
    print(f"[Screenshot] Saved full-page screenshot as {filename}")