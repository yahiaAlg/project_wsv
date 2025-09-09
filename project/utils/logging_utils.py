"""
Logging and modal injection utilities.
"""

def inject_modal(driver, text, color):
    """Injects a modal in the top-right corner with given text and background color, disappears in 3 seconds."""
    js_script = f"""
    var modal = document.createElement('div');
    modal.innerText = "{text}";
    modal.style.position = 'fixed';
    modal.style.top = '10px';  // Top position
    modal.style.right = '10px'; // Right position
    modal.style.backgroundColor = '{color}';
    modal.style.padding = '15px 25px';
    modal.style.borderRadius = '10px';
    modal.style.color = 'white';
    modal.style.fontSize = '18px';
    modal.style.textAlign = 'center';
    modal.style.boxShadow = '0px 4px 8px rgba(0,0,0,0.2)';
    modal.style.zIndex = '1000';
    modal.style.opacity = '1';
    modal.style.transition = 'opacity 0.5s ease-out';
    document.body.appendChild(modal);
    
    setTimeout(function() {{
        modal.style.opacity = '0';
        setTimeout(function() {{
            modal.remove();
        }}, 500);
    }}, 3000);
    """
    driver.execute_script(js_script)


def inject_js_model(driver, message):
    js_code = f'''
    (function() {{
        let modal = document.createElement("div");
        modal.style.position = "fixed";
        modal.style.top = "10px";
        modal.style.right = "10px";
        modal.style.backgroundColor = "
        modal.style.color = "white";
        modal.style.padding = "15px";
        modal.style.borderRadius = "5px";
        modal.style.boxShadow = "0px 0px 10px rgba(0,0,0,0.5)";
        modal.style.fontFamily = "Arial, sans-serif";
        modal.style.zIndex = "9999";
        modal.innerText = "Generated URL: {message}";
        document.body.appendChild(modal); alert("{message}")
    }})();
    '''
    driver.execute_script(js_code)