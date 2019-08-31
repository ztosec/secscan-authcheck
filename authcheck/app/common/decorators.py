import functools
from app.conf.conf import logger
from flask import redirect, request, session, url_for, render_template


def login_check(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for("web.login"))
        logger.info("{} {}".format(session.get('username'), request.url))
        return func(*args, **kwargs)

    return wrapper


def policy_check(*policies, method=None):
    """
    权限校验（请求方法为 method 时，校验当前角色是否合理）
    @:param policies: 接收PolicyEnum的枚举信息
    @param method: 校验方法
    """

    def check(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for("web.login"))
            if not method or request.method == method:  # 不设置method或当前请求方法匹配时
                for r in policies:
                    if r.value not in session['role']:
                        return redirect(url_for("web.login"))
            logger.info("{} {}".format(session.get("username"), request.url))
            return func(*args, **kwargs)

        return wrapper

    return check


def compose_route(route, *decs):
    """
    联合包装器
    :param route: app.route、blueprint.route
    :param decs:
    :return:
    """

    def func_route(rule, **options):
        def wrapper(func):
            for dec in reversed(decs):
                func = dec(func)
            return route(rule, **options)(func)

        return wrapper

    return func_route


def templated(template=None):
    """
    模板装饰器
    :param template:
    :return:
    """

    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint \
                                    .replace('.', '/') + '.html'
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                return ctx
            return render_template(template_name, **ctx)

        return decorated_function

    return decorator
