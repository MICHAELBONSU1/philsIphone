"""Check Jinja2 syntax for all delivery templates."""
import sys, os
sys.path.insert(0, r"C:\Users\user\Desktop\phils iphone\backend")

from flask import Flask
from jinja2 import Environment, FileSystemLoader

try:
    env = Environment(
        loader=FileSystemLoader(r"C:\Users\user\Desktop\phils iphone\templates"),
        autoescape=True,
    )
    for tpl in ["delivery_sender.html", "delivery_recipient.html",
                "delivery_recipient_senderid.html", "post_item.html"]:
        src, _, _ = env.get_source(env.loader, tpl)
        env.parse(src)
        print(f"  OK: {tpl}")
except Exception as e:
    print(f"  FAIL: {e}")
    import traceback; traceback.print_exc()
