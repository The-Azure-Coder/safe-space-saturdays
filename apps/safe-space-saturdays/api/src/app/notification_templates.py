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
