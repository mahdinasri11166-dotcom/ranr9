افزودن ابزار سفارشی
====================

هر فایل .py در این پوشه به‌صورت خودکار به‌عنوان ابزار لود می‌شود.

روش ۱ — یک تابع run:
--------------------
# my_tool.py
def run(text: str = "", **kwargs):
    return {"ok": True, "echo": text, "extra": kwargs}

نام ابزار = نام فایل (my_tool)

روش ۲ — چند ابزار در یک فایل:
-----------------------------
# pack.py
def hello(name="world", **kw):
    return {"ok": True, "msg": f"hello {name}"}

def add(a=0, b=0, **kw):
    return {"ok": True, "sum": float(a) + float(b)}

TOOLS = {
    "hello": hello,
    "add": add,
}

بعد از ذخیره، یک‌بار برنامه را restart کنید (CHAT.bat).
ابزارها در Agent / execute_tool در دسترس‌اند.

مسیرهای خارج از workspace در حالت unrestricted (فعلاً روشن) مجاز است.
