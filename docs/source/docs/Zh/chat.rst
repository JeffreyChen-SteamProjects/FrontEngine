Chat Page
----

.. image:: image/chat.png


*  How to use chat on FrontEngine
*  First Collect cookies
    a) (Easy) Install the latest version of Microsoft Edge
    b) (Advanced) Alternatively, you can use any browser and set the user-agent to look like you're using Edge (e.g., Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.51). You can do this easily with an extension like "User-Agent Switcher and Manager" for Chrome and Firefox.

    * Get a browser that looks like Microsoft Edge.
    * Open bing.com/chat
    * If you see a chat feature, you are good to continue...
    * Install the cookie editor extension for Chrome or Firefox
    * Go to bing.com/chat
    * Open the extension
    * Click "Export" on the bottom right, then "Export as JSON" (This saves your cookies to clipboard)
    * Paste your cookies into a file bing_cookies.json.
    * NOTE: The cookies file name MUST follow the regex pattern bing_cookies.json, so that they could be recognized by internal cookie processing mechanisms
    * Place the cookie file in the installation folder.

* Then restart FrontEngine.
    * If there is a chat error, an error message will be displayed on the control panel.
    * You can open issue on https://github.com/Integration-Automation/FrontEngine/issues

* Buttons
    * New topic
        * Clear old chat and Start new Bing chat
    * Load scene file
        * Load and start scene
    * Open voice input ui
        * Show dialog that can listen voice and sent text to Bing chat
    * Start chat
        * Start new chat