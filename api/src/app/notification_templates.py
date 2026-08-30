from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from html import escape


def _shell(*, eyebrow: str, title: str, body: str, action_label: str, action_url: str) -> str:
    safe_url = escape(action_url, quote=True)
    return f"""<!doctype html>
<html lang="en"><body style="margin:0;background:#f4eee7;color:#19352b;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:28px 12px;background:#f4eee7;"><tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fffdf8;border:1px solid #ddd6c9;border-radius:20px;overflow:hidden;">
      <tr><td style="height:8px;background:#7a8c69;font-size:0;">&nbsp;</td></tr>
      <tr><td style="padding:30px 34px 36px;">
        <p style="margin:0 0 10px;color:#7a8c69;font-size:12px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;">{escape(eyebrow)}</p>
        <h1 style="margin:0 0 16px;font-family:Georgia,serif;font-size:30px;line-height:1.2;">{title}</h1>
        {body}
        <a href="{safe_url}" style="display:inline-block;margin-top:24px;padding:14px 22px;border-radius:11px;background:#d87958;color:#fffdf8;font-size:15px;font-weight:bold;text-decoration:none;">{escape(action_label)}</a>
        <p style="margin:26px 0 0;color:#9a9f99;font-size:12px;line-height:1.5;">You are receiving this because email notifications are enabled for your Safe Space Saturdays account.</p>
      </td></tr>
    </table>
  </td></tr></table>
</body></html>"""


def weekly_performers_email(
    *, winners: Sequence[tuple[int, str, int]], period_start: date, action_url: str
) -> tuple[str, str]:
    podium_colors = ("#f1c48c", "#cbd5cf", "#df9b72")
    podium = "".join(
        f'<tr><td style="padding:10px 12px;border-bottom:1px solid #e6e0d6;">'
        f'<span style="display:inline-block;width:28px;height:28px;margin-right:10px;border-radius:50%;background:{podium_colors[index]};color:#19352b;text-align:center;line-height:28px;font-weight:bold;">{index + 1}</span>'
        f'<strong>{escape(name)}</strong><span style="float:right;color:#7a8c69;font-weight:bold;">{xp:,} XP</span>'
        "</td></tr>"
        for index, (_, name, xp) in enumerate(winners)
    )
    body = (
        f'<p style="margin:0 0 20px;color:#59645d;font-size:16px;line-height:1.6;">'
        f'Here are this week\'s community standouts, starting {period_start.strftime("%B %-d")}.</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #ddd6c9;border-radius:14px;overflow:hidden;background:#f8f6ef;">{podium}</table>'
    )
    html = _shell(
        eyebrow="Community podium",
        title="A little applause for this week’s leaders.",
        body=body,
        action_label="See the leaderboard",
        action_url=action_url,
    )
    text_rows = "\n".join(f"{index}. {name} — {xp:,} XP" for index, (_, name, xp) in enumerate(winners, 1))
    text = (
        f"This week's Safe Space Saturdays leaders (week starting {period_start.isoformat()}):\n\n"
        f"{text_rows}\n\nSee the leaderboard: {action_url}"
    )
    return html, text


DAILY_CHECKIN_MESSAGES = {
    "Sunday": "A new week does not need a perfect beginning. Take one quiet minute to notice how you are arriving today.",
    "Monday": "Before the week gathers speed, give yourself a gentle pause. There is no wrong answer—just an honest check-in.",
    "Tuesday": "You have made it to Tuesday. Notice one feeling, one need, or one small thing that is helping you keep going.",
    "Wednesday": "Midweek is a good time to come back to yourself. A few thoughtful words can make the rest of the week feel lighter.",
    "Thursday": "Take a soft moment for yourself today. You can check in without fixing anything or having all the answers.",
    "Friday": "You are here at the end of another week. Celebrate what you carried, and give yourself space for what you still need.",
    "Saturday": "Make a little room for rest and reflection today. Safe Space Saturdays is here whenever you feel ready to check in.",
}


def daily_checkin_email(*, day_name: str, action_url: str) -> tuple[str, str]:
    message = DAILY_CHECKIN_MESSAGES[day_name]
    body = (
        f'<p style="margin:0 0 18px;color:#59645d;font-size:16px;line-height:1.65;">{escape(message)}</p>'
        '<div style="padding:16px 18px;border-radius:13px;background:#edf1e7;color:#59645d;font-size:14px;line-height:1.6;">'
        "There is no pressure to write a lot. A mood and a few words are enough.</div>"
    )
    html = _shell(
        eyebrow=f"{day_name} check-in",
        title="How are you arriving today?",
        body=body,
        action_label="Take a gentle check-in",
        action_url=action_url,
    )
    text = f"{message}\n\nThere is no pressure to write a lot. A mood and a few words are enough.\n\nTake your check-in: {action_url}"
    return html, text


def csec_exam_results_email(
    *, player_name: str, percentage: float, paper_one_score: int, paper_one_total: int,
    paper_two_score: int, paper_two_total: int, breakdown: Sequence[dict[str, str]],
) -> tuple[str, str]:
    rows = "".join(
        f'<tr><td style="padding:9px;border-bottom:1px solid #e6e0d6;">{escape(item["section"])} · {escape(item["question"])}</td>'
        f'<td style="padding:9px;border-bottom:1px solid #e6e0d6;">{escape(item["result"])}</td>'
        f'<td style="padding:9px;border-bottom:1px solid #e6e0d6;">{escape(item["feedback"])}</td></tr>'
        for item in breakdown
    )
    body = (
        f'<p style="margin:0 0 18px;color:#59645d;font-size:16px;line-height:1.6;">Hi {escape(player_name)}, your CSEC IT Mock Exam has been graded.</p>'
        f'<div style="padding:18px;border-radius:14px;background:#edf1e7;text-align:center;"><strong style="font-size:34px;color:#19352b;">{percentage:.1f}%</strong><br><span style="color:#59645d;">Final percentage</span></div>'
        f'<p style="color:#59645d;line-height:1.6;">Paper 1: {paper_one_score}/{paper_one_total}<br>Paper 2: {paper_two_score}/{paper_two_total}</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #ddd6c9;border-radius:12px;overflow:hidden;font-size:13px;"><tr style="background:#f8f6ef;"><th align="left" style="padding:9px;">Question</th><th align="left" style="padding:9px;">Result</th><th align="left" style="padding:9px;">Feedback</th></tr>{rows}</table>'
    )
    html = _shell(eyebrow="CSEC exam results", title="Your exam breakdown is ready.", body=body, action_label="Open Safe Space Saturdays", action_url="/")
    text_rows = "\n".join(f'{item["section"]} · {item["question"]}: {item["result"]} — {item["feedback"]}' for item in breakdown)
    text = f"Hi {player_name}, your CSEC IT Mock Exam has been graded.\n\nFinal percentage: {percentage:.1f}%\nPaper 1: {paper_one_score}/{paper_one_total}\nPaper 2: {paper_two_score}/{paper_two_total}\n\n{text_rows}\n\nA downloadable CSV breakdown is attached."
    return html, text
