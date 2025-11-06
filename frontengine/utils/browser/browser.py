import webbrowser


def open_browser(url: str) -> bool:
    """
    開啟預設瀏覽器並導向指定的 URL
    Open the default web browser and navigate to the given URL

    :param url: 要開啟的網址 (The URL to open)
    :return: 是否成功開啟 (True if successful, False otherwise)
    """
    try:
        # 使用系統預設瀏覽器開啟網址
        # Use the system default browser to open the URL
        result = webbrowser.open(url, new=0)
        return result
    except Exception as error:
        # 若開啟失敗，印出錯誤訊息
        # Print error message if opening fails
        print(f"Failed to open browser: {error}")
        return False