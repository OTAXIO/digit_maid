def get_response(user_input):
    """
    简单的对话响应逻辑。
    未来可以接入 LLM APIs。
    """
    user_input = user_input.lower()
    
    if "你好" in user_input or "hello" in user_input:
        return "你好呀！我是你的桌面小管家。"
    elif "再见" in user_input or "bye" in user_input:
        return "拜拜！有事再叫我哦。"
    elif "名字" in user_input:
        return "我叫 DigitMaid，你可以叫我 D-Maid。"
    else:
        return "虽然我现在还不太会聊天，但我能帮你整理桌面和打开软件哦！"
