# نمونه ابزار کاربر — بدون محدودیت داخلی
def run(message: str = "hello", **kwargs):
    return {"ok": True, "echo": message, "kwargs": kwargs}


TOOLS = {
    "echo_custom": run,
}
