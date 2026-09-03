# -*- coding: utf-8 -*-
"""Login/sessiya va huquqlarni tekshirish uchun yordamchi funksiyalar."""
from functools import wraps

from flask import redirect, session, url_for, abort
from werkzeug.security import check_password_hash

import db


def authenticate(username, password):
    user = db.get_user_by_username(username)
    if not user or not user["is_active"]:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


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
