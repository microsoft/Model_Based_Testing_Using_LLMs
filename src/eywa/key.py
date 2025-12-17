
def get_key():
    with open("openai_key.txt", "r") as f:
        return f.read().strip()