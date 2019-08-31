import time
import json
import base64
from json import JSONDecodeError
from app.model.po import *
from flask import session


def str_show(s):
    """
    展示字符串
    :param s:
    :return:
    """
    return '' if not s else str(s)


def format_json(data):
    """
    格式化json
    :param data:
    :return:
    """
    if isinstance(data, str):
        data = json.loads(data)
    return json.dumps(data, indent=4, ensure_ascii=False)


def format_request(request: Request):
    """
    格式化request
    :param request:
    :return:
    """
    if not request:
        return "None"
    content = request.body_content
    if request.body_type == 'json':
        try:
            if isinstance(content, str):
                content = json.loads(content)
            content = format_json(content)
        except JSONDecodeError:
            pass
    elif request.body_type == 'byte':
        content = str(base64.b64decode(content))
    return "{} {}\n{}\n\n{}".format(request.method, request.url, format_json(request.header), content)


def format_response(response: Response):
    """
    格式化response
    :param response:
    :return:
    """
    if response is None:
        return "None"
    content = response.body_content
    if response.body_type == 'json':
        try:
            if isinstance(content, str):
                content = json.loads(content)
            content = format_json(content)
        except JSONDecodeError:
            pass
    if response.body_type == 'byte':
        content = str(base64.b64decode(response.body_content))
    return "{}\n{}\n\n{}".format(response.status_code, format_json(response.header), content)


def system_types():
    """
    系统类型（工作空间类型）
    :return:
    """
    return Workspace.sys_types().values()


def workspace_status():
    """
    工作空间状态
    :return:
    """
    return Workspace.ws_status().values()


def time_show(t):
    """
    格式化输出日期
    :param t:
    :return:
    """
    return time.ctime(t)


def time_now():
    return time.ctime()


def request_num(ws_id):
    return PacketRecord.objects(ws_id=ws_id).count()


def ws_roles(ws_id, ws_type) -> str:
    """
    获取workspace下的角色名称
    :param ws_id:
    :param ws_type: 工作空间类型
    :return:
    """
    roles = []
    if ws_type == Workspace.TYPE_DIRECT:  # WorkspaceAuth
        auth = WorkspaceAuth.objects(ws_id=ws_id)
        if len(auth) == 0:
            return ""
        auth = auth[0]

        for ai in auth.auth_info:
            roles.append(ai.describe)
    else:
        sso = WorkspaceSso.objects(ws_id=ws_id)
        if len(sso) == 0:
            return ""
        sso = sso[0]

        for a_id, desc in sso.roles.items():
            if desc:
                roles.append(desc)
            else:
                r = SsoAccount.objects(id=a_id)[0]
                roles.append(r.username if not r.describe else r.describe)
    return ', '.join(roles)


def func_account():
    """
    获取账号列表
    :return:
    """
    rest = []
    for account in SsoAccount.objects():
        assert isinstance(account, SsoAccount)
        rest.append({
            'id': str(account.id),
            'username': account.username,
            'describe': account.describe,
            'status': account.status
        })
    return rest


def is_manager():
    from app.model.model import PolicyEnum
    if PolicyEnum.MANAGE.value in session['role']:
        return True
    return False


__all__ = [
    'str_show', 'format_json', 'format_request', 'format_response', 'system_types',
    'workspace_status', 'time_show', 'ws_roles', 'func_account', 'request_num',
    'time_now', 'is_manager'
]
