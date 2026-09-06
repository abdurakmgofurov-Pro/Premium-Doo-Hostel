# -*- coding: utf-8 -*-
"""Login/sessiya va huquqlarni tekshirish uchun yordamchi funksiyalar."""
import secrets
from functools import wraps

from flask import redirect, session, url_for, abort
from werkzeug.security import check_password_hash, generate_password_hash

import db

# Foydalanuvchi nomi mavjud bo'lmaganda ham xash tekshiruvi (asta ishlaydigan
# amal) bajarilishi uchun — aks holda mavjud/mavjud bo'lmagan login orasidagi
# javob vaqti farqi orqali haqiqiy foydalanuvchi nomlarini "taxmin qilish"
# (enumeration) mumkin bo'lardi.
_DUMMY_HASH = generate_password_hash(secrets.token_hex(16))


def authenticate(username, password):
    user = db.get_user_by_username(username)
    valid_user = user if (user and user["is_active"]) else None
    password_ok = check_password_hash(
        valid_user["password_hash"] if valid_user else _DUMMY_HASH, password
    )
    if not valid_user or not password_ok:
        return None
    return valid_user


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    user = db.get_user_by_id(uid)
    if not user or not user["is_active"]:
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=_safe_path()))
        return view(*args, **kwargs)
    return wrapped


def super_admin_required(view):
    """Foydalanuvchilar/Rollar/Sozlamalar/Dollar kursi/Oy yopish kabi
    ATAYLAB rollar matritsasiga kiritilmagan, faqat Super Admin uchun
    ochiq bo'limlar uchun — bu qo'lda ~25 marta takrorlanadigan
    `if current_user()["role"] != "super_admin": abort(403)` tekshiruvi
    o'rniga; bitta joyda saqlanishi kelajakda bironta marshrutda shu
    tekshiruv sahv bilan tushib qolib ketish xavfini kamaytiradi."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login", next=_safe_path()))
        if user["role"] != "super_admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def permission_required(module, action):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=_safe_path()))
            if not db.has_permission(user, module, action):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _safe_path():
    from flask import request
    return request.path


def get_csrf_token():
    """Sessiyaga bog'langan CSRF tokeni — birinchi chaqiruvda yaratiladi,
    keyin shu sessiya davomida o'zgarmaydi. Har bir shablonda `{{
    csrf_token() }}` orqali chiqariladi, POST formalarga bazaviy
    shablonning umumiy JS orqali avtomatik qo'shiladi."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
    return token


def csrf_valid(request):
    """Formadan (`csrf_token` maydoni) yoki JS `fetch` so'rovi headeridan
    (`X-CSRFToken`) kelgan tokenni sessiyadagi bilan solishtiradi."""
    token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    expected = session.get("csrf_token")
    return bool(expected) and token == expected
