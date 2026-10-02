from datetime import datetime


BRAND_NAVY = "#0a1a33"
BRAND_NAVY_DEEP = "#060f1f"
BRAND_GOLD = "#b8944a"
BRAND_GOLD_SOFT = "#d4af6a"
BRAND_CREAM = "#f8f6f1"
BRAND_TEXT = "#2a2a35"
BRAND_MUTED = "#7a8699"

SITE_URL = "https://dynastyfc.co.za"
PHONE = "+27 63 911 1277"
EMAIL = "dynastyfcadmin@gmail.com"
INSTAGRAM = "https://www.instagram.com/dynastyfc_2016"
ADDRESS = "Fiat Grounds, Soweto, Johannesburg, South Africa"


def render_email(
    title: str,
    body_html: str,
    preview: str = "",
    cta_text: str = "Visit Dynasty FC",
    cta_url: str = SITE_URL
) -> str:
    year = datetime.now().year

    preview_block = ""
    if preview:
        preview_block = (
            f'<div style="display:none;font-size:1px;color:#ffffff;'
            f'line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">'
            f'{preview}</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
{preview_block}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f4f6f9;padding:32px 16px;">
<tr>
<td align="center">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 8px 30px rgba(10,26,51,0.08);">

<tr>
<td style="background:{BRAND_NAVY_DEEP};padding:34px 32px 30px;text-align:center;">
<div style="font-size:11px;letter-spacing:5px;color:{BRAND_GOLD_SOFT};font-weight:700;text-transform:uppercase;margin-bottom:14px;">
Dynasty Football Club
</div>
<div style="font-size:28px;font-weight:800;color:#ffffff;line-height:1.2;letter-spacing:-0.5px;">
Dynasty <span style="color:{BRAND_GOLD_SOFT};">FC</span>
</div>
<div style="width:60px;height:3px;background:{BRAND_GOLD};margin:18px auto 0;border-radius:2px;"></div>
</td>
</tr>

<tr>
<td style="padding:38px 40px 8px;">
<h1 style="margin:0 0 20px;font-size:22px;color:{BRAND_NAVY};font-weight:700;line-height:1.3;letter-spacing:-0.3px;">
{title}
</h1>
</td>
</tr>

<tr>
<td style="padding:0 40px 30px;color:{BRAND_TEXT};font-size:15px;line-height:1.75;font-weight:400;">
{body_html}
</td>
</tr>

<tr>
<td style="padding:0 40px 40px;text-align:center;">
<a href="{cta_url}" style="display:inline-block;padding:14px 40px;background:{BRAND_GOLD};color:{BRAND_NAVY};font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:2px;text-decoration:none;border-radius:30px;">
{cta_text}
</a>
</td>
</tr>

<tr>
<td style="background:{BRAND_CREAM};padding:28px 40px 24px;text-align:center;border-top:1px solid #ece5d6;">
<div style="color:{BRAND_NAVY};font-size:14px;font-weight:700;margin-bottom:6px;">
Fiat Grounds, Soweto
</div>
<div style="color:{BRAND_MUTED};font-size:13px;line-height:1.9;">
Johannesburg, South Africa<br />
<a href="tel:{PHONE}" style="color:{BRAND_MUTED};text-decoration:none;">{PHONE}</a> &nbsp;•&nbsp;
<a href="mailto:{EMAIL}" style="color:{BRAND_MUTED};text-decoration:none;">{EMAIL}</a><br />
<a href="{INSTAGRAM}" style="color:{BRAND_GOLD};text-decoration:none;font-weight:600;">@dynastyfc_2016</a>
</div>
</td>
</tr>

<tr>
<td style="background:{BRAND_NAVY_DEEP};padding:18px 40px;text-align:center;">
<div style="color:{BRAND_MUTED};font-size:11px;letter-spacing:1.5px;text-transform:uppercase;">
&copy; {year} Dynasty Football Club &nbsp;•&nbsp; All rights reserved
</div>
</td>
</tr>

</table>

</td>
</tr>
</table>
</body>
</html>"""


def info_block(label: str, value: str) -> str:
    if not value:
        return ""
    return (
        f'<div style="margin-bottom:14px;">'
        f'<div style="font-size:11px;letter-spacing:2px;color:{BRAND_GOLD};'
        f'text-transform:uppercase;font-weight:700;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:15px;color:{BRAND_NAVY};font-weight:600;">{value}</div>'
        f'</div>'
    )


def message_block(text: str) -> str:
    if not text:
        return ""
    return (
        f'<div style="margin-top:18px;padding:18px 22px;background:{BRAND_CREAM};'
        f'border-left:3px solid {BRAND_GOLD};border-radius:6px;'
        f'color:{BRAND_TEXT};font-size:15px;line-height:1.75;white-space:pre-wrap;">'
        f'{text}'
        f'</div>'
    )