import pickle

import redis
import requests

from app import redis_pool
from app.conf.conf import logger, session_timeout, proxies, timeout
from app.common.util import gen_banner
from app.model.po import SsoAccount, WorkspaceSso, PacketRecord, Workspace, PacketData, Request, Response
from app.model.exception import LibException, ParserException, AccountException
from app.model.model import HeaderModel, BodyModel, requests_request, AuthSession


def verify_account(ais: list):
    """
    校验账号是否存在且有效
    :param ais: [account.id, account.id, ...]
    :return:
    """
    assert isinstance(ais, list)
    valid_num = SsoAccount.objects(id__in=ais, status=SsoAccount.STATUS_VALID).count()
    return valid_num == len(ais)


def workspace_sso_conf(_id, data):
    """
    配置工作空间（示例sso认证）
    :param _id:
    :param data:
    :return:
    """
    ts = WorkspaceSso.objects(ws_id=_id)
    if len(ts) == 0:  # 之前没有，新录入
        ws = WorkspaceSso()
        ws.ws_id = _id
    else:
        ws = ts[0]
    if not isinstance(data.get('roles'), dict):
        raise LibException('请至少选择一个账号！')
    ws.roles = data.get('roles')
    ws.redirect_url = data.get('redirect_url')
    ws.portal_site = data.get('portal_site')
    ws.save()


def deal_with_sso(header: HeaderModel, body: BodyModel, name, packet_record: PacketRecord,
                  sso: WorkspaceSso, ws: Workspace):
    """
    处理sso认证的系统
    :param header:
    :param body:
    :param name:
    :param packet_record:
    :param sso:
    :param ws:
    :return:
    """
    rs = redis.Redis(connection_pool=redis_pool)
    hm_key = "{}:{}".format(name, ws.id)  # session
    logger.info("{} deal with sso: {}".format(name, header.url))
    _header = header.header
    if 'Cookie' in _header.keys():
        _header.pop('Cookie')

    for account_id, describe in sso.roles.items():
        account = SsoAccount.objects(id=account_id)
        if len(account) == 0:
            logger.error("no {}->{}!".format(account_id, describe))
            continue
        account = account[0]
        assert isinstance(account, SsoAccount)
        _r = describe if describe else account.describe if account.describe else account.username

        try:
            if account.username == '-':  # 空角色
                if body.type == BodyModel.TYPE_JSON:
                    raw_rest = requests_request(header.method, header.url, json=body.body(), headers=_header)
                elif body.type in [BodyModel.TYPE_FORM, BodyModel.TYPE_BYTE]:
                    raw_rest = requests_request(header.method, header.url, json=body.body(), headers=_header)
                else:
                    raise ParserException("Illegal body type{}".format(body.type))
            else:  # 正常账号
                auth_session = rs.hmget(hm_key, str(account.id))[0]
                if not auth_session:
                    session = legalize_ws(account, sso)
                    auth_session = AuthSession(session, account)

                    rs.hset(hm_key, str(account.id), pickle.dumps(auth_session))
                else:
                    auth_session = pickle.loads(auth_session)

                rs.expire(hm_key, 60 * session_timeout)  # 重设超时时间

                if body.type == body.TYPE_JSON:
                    raw_rest = auth_session.request(header.method, header.url, json=body.body(), headers=_header)
                elif body.type in [BodyModel.TYPE_FORM, BodyModel.TYPE_BYTE]:
                    raw_rest = auth_session.request(header.method, header.url, data=body.body(), headers=_header)
                else:
                    raise ParserException('Illegal body type {}'.format(body.type))
        except Exception as e:
            logger.error("{} {} processing error!".format(account_id, describe), exc_info=True)

            if isinstance(e, AccountException):  # 账号失效
                account.status = SsoAccount.STATUS_INVALID
                account.save()
            packet_data = PacketData(banner=gen_banner(_r, header.method, header.url, str(e)), role_describe=_r)
            packet_data.save()
            packet_record.per_packets.append(packet_data)
        else:
            resp_body = BodyModel(raw_rest.content, charset=raw_rest.encoding)
            packet_data = PacketData(banner=gen_banner(_r, header.method, header.url, raw_rest.text),
                                     role_describe=_r,
                                     request=Request(url=header.url, method=header.method,
                                                     header=raw_rest.request.headers,
                                                     body_content=body.content, body_type=body.type),
                                     response=Response(status_code=raw_rest.status_code, header=raw_rest.headers,
                                                       body_content=resp_body.content, body_type=resp_body.type))
            packet_data.save()
            packet_record.per_packets.append(packet_data)


def legalize_ws(account: SsoAccount, sso: WorkspaceSso) -> requests.Session:
    """
    使用该账号认证该工作空间
    :param account:
    :param sso:
    :return: session
    """
    logger.info("{} 工作空间认证：".format(account.username, sso.ws_id))
    session = requests.Session()
    try:

        rest = session.get(sso.portal_site, proxies=proxies, verify=False, timeout=timeout)

        session.post(rest.url, data={
            'username': account.username,
            'password': account.password,
            'confirm': 'yes'
        }, proxies=proxies, verify=False, timeout=timeout)

    except Exception as e:
        raise AccountException(e)
    return session


def _sso_password_verify(username, password):
    """
    可在此处校验密码是否正确
    :param username:
    :param password:
    :return:
    """
    # ...
    return True


def sso_account_record(username, password, describe, _id=None):
    """
    记录 sso 账号信息
    :param username: 用户名
    :param password: 密码
    :param describe: 角色描述
    :param _id: 若有，则更新，否则添加
    :return:
    """
    if not username:
        raise AccountException("未知用户名！")

    if username != '-':  # 默认可存储空账号
        if not _sso_password_verify(username, password):
            raise AccountException("无效的密码！")

    if _id:  # 更新
        sso_accounts = SsoAccount.objects(id=_id)
        if len(sso_accounts) != 1:
            raise AccountException("未找到对应账号信息")
        sso_account = sso_accounts[0]
    else:
        sso_account = SsoAccount()
    sso_account.username = username
    sso_account.password = password
    sso_account.describe = describe
    sso_account.status = SsoAccount.STATUS_VALID
    sso_account.save()


__all__ = [
    "verify_account", "workspace_sso_conf", "deal_with_sso", "legalize_ws", "sso_account_record"
]
