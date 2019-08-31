import copy
import re

from app.conf.conf import logger
from app.common.util import gen_banner
from app.model.po import WorkspaceAuth, AuthInfo, PacketRecord, PacketData, Request, Response
from app.model.exception import ParserException
from app.model.model import HeaderModel, BodyModel, requests_request


def workspace_auth_conf(_id, workspace_auth):
    """
    配置工作空间（手动录入认证信息）
    :param _id:
    :param workspace_auth:
    :return:
    """
    ts = WorkspaceAuth.objects(ws_id=_id)
    if len(ts) == 0:  # 之前没有，新录入
        wa = WorkspaceAuth()
        wa.ws_id = _id
    else:
        wa = ts[0]

    wa.auth_info = []
    for _ in workspace_auth:
        auth_info = AuthInfo()
        auth_info.describe = _.get('describe')
        auth_info.url_pattern = _.get('url_pattern')
        auth_info.auth_header = _.get('auth_header')
        auth_info.auth_args = _.get('auth_args')
        auth_info.auth_param = _.get('auth_param')

        wa.auth_info.append(auth_info)
    wa.save()


def deal_with_direct(header: HeaderModel, body: BodyModel, name, packet_record: PacketRecord,
                     auth: WorkspaceAuth):
    """
    手动录入认证信息
    :param header:
    :param body:
    :param name:
    :param packet_record:
    :param auth:
    :return:
    """
    logger.info("{} deal with direct: {}".format(name, header.url))
    for auth_info in auth.auth_info:
        assert isinstance(auth_info, AuthInfo)
        if auth_info.url_pattern and not re.match(auth_info.url_pattern, header.url):  # url_pattern
            continue
        _header = copy.copy(header)
        _body = copy.copy(body)
        try:
            if auth_info.auth_args:
                _header.update_args(auth_info.auth_args)
            if auth_info.auth_header:
                _header.update_headers(auth_info.auth_header)
            if auth_info.auth_param:
                _body.update_param(auth_info.auth_param)

            if _body.type == BodyModel.TYPE_JSON:
                raw_rest = requests_request(_header.method, _header.url, json=_body.body(), headers=_header.header)
            elif _body.type in [BodyModel.TYPE_FORM, BodyModel.TYPE_BYTE]:
                raw_rest = requests_request(_header.method, _header.url, data=_body.body(), headers=_header.header)
            else:
                raise ParserException("illegal body type {}".format(_body.type))
        except Exception as e:
            logger.error("{} processing error!".format(auth_info.describe), exc_info=True)

            packet_data = PacketData(banner=gen_banner(auth_info.describe, _header.method, _header.url, str(e)),
                                     role_describe=auth_info.describe)
            packet_data.save()
            packet_record.per_packets.append(packet_data)
        else:
            resp_body = BodyModel(raw_rest.content, charset=raw_rest.encoding)
            packet_data = PacketData(banner=gen_banner(auth_info.describe, _header.method, _header.url,
                                                       raw_rest.text), role_describe=auth_info.describe,
                                     request=Request(url=_header.url, method=_header.method, header=_header.header,
                                                     body_content=_body.content, body_type=_body.type),
                                     response=Response(status_code=raw_rest.status_code, header=raw_rest.headers,
                                                       body_content=resp_body.content, body_type=resp_body.type))
            packet_data.save()
            packet_record.per_packets.append(packet_data)


__all__ = [
    "workspace_auth_conf", "deal_with_direct"
]
