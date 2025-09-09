"""
Network/Wi-Fi management functions.
"""

import subprocess
import requests
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import concurrent.futures
from config import wifi_interfaces, profile_paths, WIFI_INTERFACES, current_index
from utils.helpers import wait_for_page_to_load


def connect_to_wifi(ssid, password):
    """
    Connect to a Wi-Fi network using macOS networksetup command.
    
    :param ssid: The name (SSID) of the Wi-Fi network.
    :param password: The password for the Wi-Fi network.
    """
    try:
        subprocess.run(["networksetup", "-setairportpower", "en0", "on"], check=True)

        result = subprocess.run(
            ["networksetup", "-setairportnetwork", "en0", ssid, password],
            capture_output=True,
            text=True,
            check=True
        )

        if result.returncode == 0:
            print(f"Successfully connected to {ssid}")
        else:
            print(f"Failed to connect to {ssid}: {result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")


def configure_all_interfaces():
    """Assigns static IP and DNS to each interface as fast as possible."""
    WIFI_INTERFACES_LOCAL = ["Wi-Fi 4", "Wi-Fi 3"]
    GATEWAY, DNS_SERVER = "192.168.0.1", "8.8.8.8"

    def configure(interface, index):
        ip_address = f"192.168.0.{10 + index}"
        print(f"🚀 Configuring {interface} -> IP: {ip_address}")

        cmds = [
            ["netsh", "interface", "ip", "set", "address", interface, "static", ip_address, "255.255.255.0", GATEWAY],
            ["netsh", "interface", "ip", "set", "dns", interface, "static", DNS_SERVER]
        ]

        processes = [subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for cmd in cmds]

        for process in processes:
            process.wait()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(WIFI_INTERFACES_LOCAL)) as executor:
        executor.map(configure, WIFI_INTERFACES_LOCAL, range(len(WIFI_INTERFACES_LOCAL)))

    print("✅ All interfaces configured in record time!")


def check_connection():
    """Checks internet connectivity by pinging Google DNS (8.8.8.8)."""
    try:
        subprocess.run(["ping", "-n", "2", "8.8.8.8"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def switch_interface():
    """Switches to a working Wi-Fi interface and verifies connectivity."""
    global current_index
    WIFI_INTERFACES_LOCAL = ["Wi-Fi 3", "Wi-Fi 4"]  
    current_index = -1

    for _ in range(len(WIFI_INTERFACES_LOCAL)):  
        current_index = (current_index + 1) % len(WIFI_INTERFACES_LOCAL)
        interface = WIFI_INTERFACES_LOCAL[current_index]

        print(f"🔄 Switching to {interface}...")
        subprocess.run(["netsh", "interface", "set", "interface", interface, "admin=enabled"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        result = subprocess.run(["netsh", "interface", "show", "interface", interface], capture_output=True, text=True)
        
        if "Connected" in result.stdout:
            print(f"✅ {interface} is connected!")
            break  


def fast_connect_wifi(primary_ssid="p1", secondary_ssid="p2"):
    import re
    try:
        interface_cmd = ["networksetup", "-listallhardwareports"]
        interface_result = subprocess.run(interface_cmd, capture_output=True, text=True).stdout
        match = re.search(r"Hardware Port: Wi-Fi\nDevice: (\S+)", interface_result)
        if not match:
            print("Wi-Fi interface not found.")
            return False
        wifi_interface = match.group(1)
        
        scan_cmd = ["system_profiler", "SPNetworkDataType"]
        result = subprocess.run(scan_cmd, capture_output=True, text=True).stdout.lower()
        
        available_ssids = re.findall(r'ssid: ([^\n]+)', result)
        available_ssids = [ssid.strip() for ssid in available_ssids]
        
        target_ssid = None
        if primary_ssid.lower() in available_ssids:
            target_ssid = primary_ssid
        elif secondary_ssid.lower() in available_ssids:
            target_ssid = secondary_ssid

        if not target_ssid:
            print("Neither p1 nor p2 are available.")
            return False

        connect_cmd = ["networksetup", "-setnetworkserviceenabled", wifi_interface, "off"]
        subprocess.run(connect_cmd, check=True)
        connect_cmd = ["networksetup", "-setnetworkserviceenabled", wifi_interface, "on"]
        subprocess.run(connect_cmd, check=True)
        connect_cmd = ["networksetup", "-setdnsservers", wifi_interface, "Empty"]
        subprocess.run(connect_cmd, check=True)
        connect_cmd = ["networksetup", "-setairportnetwork", wifi_interface, target_ssid]
        subprocess.run(connect_cmd, check=True)
        print(f"Connected to {target_ssid}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error connecting to Wi-Fi: {e}")
        return False


def send_reboot_request2(driver):
    driver = driver
    
    try:
        driver.get("http://192.168.0.1/login.htm")
        time.sleep(2)
        wait_for_page_to_load(driver=driver)
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys("admin")

        driver.find_element(By.ID, "password").send_keys("rootira0")
        time.sleep(2)
        
        driver.find_element(By.ID, "logIn_btn").click()
        print("✅ Login successful")

        driver.get("http://192.168.0.1/saveconf.htm")
        print("✅ Navigated directly to the reboot page!")

        reboot_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "reboot"))
        )

        driver.execute_script("arguments[0].click();", reboot_button)  
        print("✅ Clicked 'Reboot' button, waiting for confirmation alert...")

        WebDriverWait(driver, 5).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"⚠️ Alert Text: {alert.text}")  
        alert.accept()  
        print("✅ Alert confirmed, router is rebooting!")
        connect_wifi()
        time.sleep(2)
        driver.quit()
    except Exception as e:
        print("❌ Error:", e)
        driver.quit()

    finally:
        driver.service.process.kill()


def check_site_status(url):
    try:
        response = requests.get(url, timeout=3)  
        if response.status_code == 302 or response.status_code ==  200:
            print(f"{url} is online.")
            return True
        else:
            print(f"{url} is reachable but returned status code: {response.status_code}")
            return False
    except requests.ConnectionError:
        print(f"{url} is offline or unreachable.")
        return False
    except requests.Timeout:
        print(f"{url} is not responding (timeout).")
        return False


def manage_network(action):
    url = 'http://192.168.8.1/reqproc/proc_post'
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'http://192.168.8.1',
        'Referer': 'http://192.168.8.1/index.html',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    data = {
        'notCallback': 'true',
        'goformId': 'DISCONNECT_NETWORK' if action == 'disconnect' else 'CONNECT_NETWORK'
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"


def send_reboot_request(driver):
    if check_site_status("http://192.168.8.1/"):
        print(manage_network('disconnect'))
        print(manage_network('connect'))
        connect_to_wifi("MOH_5G", "rootira2026")
    else:
        try:
            driver.get("http://192.168.1.254/login.cgi")
            wait_for_page_to_load(driver)  

            username_input = driver.find_element(By.ID, "username")
            username_input.send_keys("userAdmin")

            password_input = driver.find_element(By.ID, "password")
            password_input.send_keys("9559270591aa")
            
            password_input.send_keys(Keys.RETURN)
            time.sleep(2)  

            driver.get("http://192.168.1.254/reboot.cgi")
            wait_for_page_to_load(driver=driver)
            
            reboot_button = driver.find_element(By.ID, "do_reboot")
            reboot_button.click()
            alert = driver.switch_to.alert
            alert.accept()
            time.sleep(2)
            driver.quit()
            if check_site_status("http://192.168.37.1/"):
                connect_to_wifi("p35", "rootira2026")

            elif check_site_status("http://192.168.0.1/"):
                connect_to_wifi("MOH_5G", "rootira2026")

            print("✅ Reboot command sent successfully!")
            time.sleep(5)

        except Exception as e:
            print("❌ Error:", e)

        finally:
            time.sleep(5)
            driver.quit()


def run_command(command):
    """Runs a command in the Windows command prompt and returns the output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)


def delete_all_profiles():
    """Deletes all existing Wi-Fi profiles from each interface."""
    print("Deleting all existing Wi-Fi profiles...")
    
    profiles_output = run_command('netsh wlan show profiles')
    
    if not profiles_output:
        print("⚠ No profiles found or command failed!")
        return

    for line in profiles_output.split("\n"):
        if "All User Profile" in line:
            try:
                profile_name = line.split(":")[1].strip()
                print(f"🗑 Deleting profile '{profile_name}'...")
                run_command(f'netsh wlan delete profile name="{profile_name}"')
            except IndexError:
                print(f"⚠ Unexpected format in line: {line}")


def add_profiles():
    """Adds the correct Wi-Fi profiles to each interface."""
    print("\nAdding Wi-Fi profiles...")
    for interface, profile_path in profile_paths.items():
        print(f"Adding profile for {interface} from {profile_path}...")
        run_command(f'netsh wlan add profile filename="{profile_path}" interface="{interface}"')


def set_manual_connection():
    """Ensures each interface only connects to its assigned SSID."""
    print("\nSetting connection mode to manual...")
    for interface, ssid in wifi_interfaces.items():
        print(f"Setting {interface} to connect only to {ssid}...")
        run_command(f'netsh wlan set profileparameter name="{ssid}" interface="{interface}" connectionmode=manual')


def block_other_ssids():
    """Blocks each interface from connecting to SSIDs other than its assigned one."""
    print("\nBlocking other SSIDs...")
    for interface, ssid in wifi_interfaces.items():
        for other_ssid in wifi_interfaces.values():
            if other_ssid != ssid:
                print(f"Blocking {interface} from connecting to {other_ssid}...")
                run_command(f'netsh wlan add filter permission=deny ssid="{other_ssid}" networktype=infrastructure interface="{interface}"')


def run_command_no_wait(command):
    """Runs a shell command without waiting for output."""
    subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_wifi():
    """Connects each interface to its assigned SSID in parallel."""
    print("\n🚀 Connecting each interface to its SSID...")

    def connect(interface, ssid):
        print(f"🔗 Connecting {interface} to {ssid}...")
        run_command_no_wait(f'netsh wlan connect name="{ssid}" interface="{interface}"')

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(wifi_interfaces)) as executor:
        executor.map(connect, wifi_interfaces.keys(), wifi_interfaces.values())

    time.sleep(3)  
    print("✅ All interfaces connected!")


def verify_connection():
    """Verifies that each interface is connected to the correct SSID."""
    print("\nVerifying Wi-Fi connections...")
    output = run_command("netsh wlan show interfaces")
    print(output)