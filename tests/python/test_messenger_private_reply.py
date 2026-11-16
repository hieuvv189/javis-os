"""Messenger: private replies to Page comments (comment mode "private").

    python tests/run.py messenger_private_reply

No network: the Graph call is faked, nothing reaches a real customer. Guarded:

  1. Private mode sends ONE private Messenger message (recipient.comment_id), never a public reply;
     reply mode on another Page still answers publicly and inbox mode still only records.
  2. Dedupe by comment id survives a restart (a fresh bot, the in-memory cache gone) and a webhook retry.
  3. A reply inside the thread and a second comment from someone who has not answered get no message;
     once they write to the Page in Messenger, their next comment may get one again.
  4. A Meta refusal (comment older than 7 days) is recorded as failed, never as sent, and not retried.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import sys
import tempfile

os.environ["JAVIS_STATE_DIR"] = tempfile.mkdtemp(prefix="javis-messenger-private-")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import messenger_bot  # noqa: E402

_fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
    if not ok:
        _fails.append(name)


PAGE = "284239018098473"
OTHER = "1234567890123"
TOKEN = "EAA" + "t" * 60
POST = f"{PAGE}_555"


def com(cid, root=None, who="777", msg="Lót này giá sao shop?"):
    return {"comment_id": cid, "root_id": root or cid, "post_id": POST, "from_id": who,
            "from_name": "Chị Lan", "message": msg, "photo": "", "video": "", "permalink": ""}


def make_bot(page, answers, calls, fail=None):
    async def answer(text, meta, progress):
        answers.append(dict(meta or {}))
        if (meta or {}).get("log_only"):
            return None
        return {"text": "**Dạ** chị cần lót cho bé mấy tháng ạ?"}

    bot = messenger_bot.MessengerBot({"page_id": page, "access_token": TOKEN, "app_secret": "c" * 32}, "",
                                     answer, giau_trang_thai=True)

    async def fake_post(client, path, payload):
        calls.append((path, payload))
        if fail:
            return {"ok": False, "code": 10, "error": fail}
        if "recipient" in payload:
            return {"ok": True, "recipient_id": "psid1", "message_id": "m_1"}
        return {"ok": True, "id": "555_900"}

    async def fake_post_text(client, post_id, instagram=False):
        return "Lót phân su Molli"
    bot._post_json = fake_post
    bot._post_text = fake_post_text
    return bot


async def turn(bot, mode, *comments):
    orig = messenger_bot.comment_mode
    messenger_bot.comment_mode = lambda aid: mode
    try:
        for c in comments:
            await bot._on_comment(c)
        for task in list(bot._current.values()):
            await task
        await asyncio.sleep(0)
    finally:
        messenger_bot.comment_mode = orig
        if bot._client:
            await bot._client.aclose()
            bot._client = None


def run(c):
    return asyncio.run(c)


check("private is a valid comment mode, the default stays inbox",
      "private" in messenger_bot.COMMENT_MODES and messenger_bot.COMMENT_MODE_DEFAULT == "inbox")

# 1. private vs public
answers, calls = [], []
bot = make_bot(PAGE, answers, calls)
run(turn(bot, "private", com("555_1"), com("555_1")))   # + webhook retry
check("private mode: one private message by comment id, plain text, no public reply",
      calls == [(f"{PAGE}/messages", {"recipient": {"comment_id": "555_1"},
                                      "message": {"text": "Dạ chị cần lót cho bé mấy tháng ạ?"}})], calls)
check("private mode: the model is told the message is private, not public",
      answers and answers[0].get("private_reply") and "RIÊNG" in answers[0].get("ghi_chu_dau", "")
      and "CÔNG KHAI" not in answers[0].get("ghi_chu_dau", ""), answers)
rec = messenger_bot.private_record(PAGE, "555_1")
check("ledger says sent with Meta's message id", rec.get("status") == "sent" and rec.get("message_id") == "m_1", rec)

# 2. restart: a brand-new bot (empty in-memory dedupe) sees the same comment again
answers2, calls2 = [], []
run(turn(make_bot(PAGE, answers2, calls2), "private", com("555_1")))
check("after a restart the same comment id sends nothing", calls2 == [] and answers2 == [], (calls2, answers2))

# 3. thread reply and waiting commenter
answers3, calls3 = [], []
run(turn(make_bot(PAGE, answers3, calls3), "private", com("555_2", root="555_1"), com("555_3")))
check("a reply in the thread and a second comment before the person answered send nothing",
      calls3 == [] and len(answers3) == 2 and all(a.get("log_only") for a in answers3), (calls3, answers3))
messenger_bot.private_answered(PAGE, "777")
answers3b, calls3b = [], []
run(turn(make_bot(PAGE, answers3b, calls3b), "private", com("555_4")))
check("once the person wrote to the Page, a new comment gets one private message",
      len(calls3b) == 1 and calls3b[0][1]["recipient"]["comment_id"] == "555_4", calls3b)

# 4. Meta refusal
answers4, calls4 = [], []
run(turn(make_bot(PAGE, answers4, calls4, fail="comment too old"), "private", com("555_9", who="888")))
rec = messenger_bot.private_record(PAGE, "555_9")
check("refusal recorded as failed with the error, not sent",
      rec.get("status") == "failed" and "too old" in rec.get("error", "") and len(calls4) == 1, rec)
answers4b, calls4b = [], []
run(turn(make_bot(PAGE, answers4b, calls4b), "private", com("555_9", who="888")))
check("a failed comment is not retried", calls4b == [], calls4b)
answers4c, calls4c = [], []
run(turn(make_bot(PAGE, answers4c, calls4c), "private", com("555_10", who="888")))
check("a failed send does not put the person on hold", len(calls4c) == 1, calls4c)

# 5. other Pages untouched
answers5, calls5 = [], []
run(turn(make_bot(OTHER, answers5, calls5), "reply", com("777_1")))
check("reply mode on another Page still answers publicly under the comment",
      calls5 == [("777_1/comments", {"message": "Dạ chị cần lót cho bé mấy tháng ạ?"})], calls5)
answers6, calls6 = [], []
run(turn(make_bot(OTHER, answers6, calls6), "inbox", com("777_2")))
check("inbox mode on another Page only records", calls6 == [] and answers6 and answers6[0].get("log_only"), answers6)
check("other Pages leave no private-reply ledger entries", messenger_bot.private_record(OTHER, "777_1") == {})

print()
if _fails:
    print(f"{len(_fails)} FAIL: {_fails}")
    sys.exit(1)
print("all ok")
