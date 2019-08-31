import redis
import hashlib
import threading
import pickle
from app import redis_pool
from app.conf.conf import *
from app.core.identify.direct import workspace_auth_conf, deal_with_direct
from app.core.identify.sso import workspace_sso_conf, deal_with_sso
from app.model.model import *
from app.model.exception import *
from app.common.util import deal_request, gen_banner
from concurrent.futures import ThreadPoolExecutor


def conf_workspace(_id, data: dict):
    """
    配置工作空间
    :param _id: 工作空间的id
    :param data: json数据
    {
        'status': 'init',
        'hosts': [host1, host2],
        'system_type': sso/direct,
        'workspace_sso': {
            'roles': {
                'account_id': describe,
                'account_id': describe,
                ...
            },
            'redirect_url': redirect_url,
            'portal_site': portal_site
        },
        'workspace_auth': [{
            'url_pattern': url_pattern,
            'describe': role_describe,
            'auth_header': {k:v, k:v},
            'auth_args': {k:v, k:v},
            'auth_param': {k:v, k:v}
        },{
        }]
    }
    :return:
    """
    if data.get('status'):  # 优先更新状态
        assert data['status'] in Workspace.ws_status().values()
        Workspace.objects(id=_id).update(status=data['status'])
        return

    system_type = data.get('system_type')
    hosts = data.get('hosts')

    if not hosts or not isinstance(hosts, list) or not system_type \
            or system_type not in Workspace.sys_types().values():
        raise LibException('请确认system_type和hosts')

    workspace = Workspace.objects(id=_id)[0]
    assert isinstance(workspace, Workspace)
    workspace.hosts = hosts
    workspace.system_type = system_type
    workspace.save()

    if system_type == Workspace.TYPE_DIRECT and data.get('workspace_auth'):
        workspace_auth_conf(_id, data['workspace_auth'])
    elif system_type == Workspace.TYPE_SSO and data.get('workspace_sso'):
        workspace_sso_conf(_id, data['workspace_sso'])


def pr_replay(name, pr: PacketRecord):
    """
    数据包重放
    :param name: username
    :param pr:
    :return: 重放后的流量包
    """

    req = pr.raw_packet.request
    assert isinstance(req, Request)

    header = HeaderModel(header=req.header, url=req.url, method=req.method)
    body = BodyModel()
    body.content = req.body_content
    body.type = req.body_type

    ws = Workspace.objects(id=pr.ws_id)[0]
    assert isinstance(ws, Workspace)

    if ws.system_type == Workspace.TYPE_DIRECT:
        auth_infos = WorkspaceAuth.objects(ws_id=ws.id)
        if len(auth_infos) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_name))
        ai = auth_infos[0]
        if len(ai.auth_info) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_name))
        roles = ai
    else:
        wos = WorkspaceSso.objects(ws_id=ws.id)
        if len(wos) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_name))
        wo = wos[0]
        if len(wo.roles.items()) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_name))
        roles = wo

    return deal_scan(name=name, header=header, body=body, ws=ws, roles=roles)


def deal_task(task: TaskModel):
    """
    处理扫描任务
    :param task: taskmodel
    :return:
    """

    try:
        header, body = deal_request(task.url, task.raw)

        if re.search(scope_exclude, header.url):  # 过滤
            return
        if header.method == 'OPTIONS':  # 过滤
            return

        host = str(header.header['Host']).strip()

        for ws in Workspace.objects(hosts=host, status=Workspace.STATUS_START, cname=task.name):
            assert isinstance(ws, Workspace)

            rs = redis.Redis(connection_pool=redis_pool)
            # 去掉完全一样的请求
            digest = hashlib.md5(str(task.raw).encode('utf-8')).digest()
            heap = rs.hget("parse_heap:{}:{}".format(task.name, str(ws.id)), digest)
            if heap:
                logger.debug("filter the same request: {}".format(task.url))
                continue
            rs.hset("parse_heap:{}:{}".format(task.name, str(ws.id)), digest, task.url)

            logger.info("deal with: {} => {}".format(task.name, task.url))
            try:
                deal_scan(task.name, header, body, ws, get_roles(ws))
            except LibException as e:
                logger.error(e)
                continue
        else:
            logger.debug("no corresponding workspace: {}".format(host))
    except Exception as e:
        logger.exception(e)


def get_roles(ws):
    """
    获取角色
    :param ws:
    :return:
    """
    if ws.system_type == Workspace.TYPE_DIRECT:
        auth_infos = WorkspaceAuth.objects(ws_id=ws.id)
        if len(auth_infos) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_name))
        ai = auth_infos[0]
        if len(ai.auth_info) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_name))
        roles = ai
    elif ws.system_type in Workspace.TYPE_SSO:
        wos = WorkspaceSso.objects(ws_id=ws.id)
        if len(wos) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_type))
        wo = wos[0]
        if len(wo.roles.items()) == 0:
            raise LibException("{} {} have no roles!".format(ws.id, ws.system_type))
        roles = wo
    else:
        raise LibException("未知的系统类型: {} {}".format(ws.id, ws.system_type))
    return roles


def deal_scan(name, header: HeaderModel, body: BodyModel, ws: Workspace, roles) -> PacketRecord:
    """
    处理扫描任务
    :param name: 流量所属人
    :param header: 原始请求头
    :param body: 原始请求体
    :param ws: 对应工作空间
    :return: {
        'name': name,
        'create_time': packet_record.create_time.ctime(),
        'raw_packet': raw_packet,
        'per_packets': per_packets
    }
    """
    if header.method not in [HeaderModel.METHOD_GET, HeaderModel.METHOD_POST, HeaderModel.METHOD_DELETE,
                             HeaderModel.METHOD_PUT]:
        logger.error("暂不支持的方法：{}".format(header.method))
        return None

    if body.type == BodyModel.TYPE_JSON:
        raw_rest = requests_request(header.method, header.url, json=body.body(), headers=header.header)
    elif body.type in [BodyModel.TYPE_FORM, BodyModel.TYPE_BYTE, BodyModel.TYPE_XML]:
        raw_rest = requests_request(header.method, header.url, data=body.body(), headers=header.header,
                                    proxies=proxies, allow_redirects=False, verify=False, timeout=timeout)
    else:
        raise ParserException('illegal body type {}'.format(body.type))

    resp_body = BodyModel(raw_rest.content, charset=raw_rest.encoding)

    request_model = Request(url=raw_rest.request.url, method=raw_rest.request.method, header=raw_rest.request.headers,
                            body_content=body.content, body_type=body.type)
    response_model = Response(status_code=raw_rest.status_code, header=raw_rest.headers,
                              body_content=resp_body.content, body_type=resp_body.type)

    rp = PacketData(banner=gen_banner("原始包", header.method, header.url, raw_rest.text),
                    role_describe="原始包", request=request_model, response=response_model)

    rp.save()
    packet_record = PacketRecord(ws_id=ws.id, username=name, raw_packet=rp)

    try:
        if ws.system_type in [Workspace.TYPE_SSO]:  # 示例sso认证
            deal_with_sso(header=header, body=body, name=name, packet_record=packet_record, sso=roles, ws=ws)
        elif ws.system_type == Workspace.TYPE_DIRECT:  # 手动输入认证信息
            deal_with_direct(header=header, body=body, name=name, packet_record=packet_record, auth=roles)
        else:
            raise ApiException('错误的系统类型: {} !'.format(ws.system_type))
    except Exception as e:
        logger.exception(e)
    else:
        packet_record.save()

    rs = redis.Redis(connection_pool=redis_pool)
    for key in rs.keys("listening:*"):
        if key.endswith(b":setting"):
            setting = rs.hgetall(key)
            setting = {k.decode('utf-8'): v.decode('utf-8') for k, v in setting.items()}
            if setting and setting.get('ws_id') == str(ws.id) and setting.get('name') == name:
                logger.debug("listening push {}: {}".format(name, ws.id))
                rs.rpush(key.strip(b':setting'), pickle.dumps(packet_record))

    return packet_record


class ScanThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.setDaemon(True)

    def run(self):
        """
        开启扫描线程
        """
        executor = ThreadPoolExecutor(max_workers=max_workers)
        rs = redis.Redis(connection_pool=redis_pool)
        while True:
            task = TaskModel(**json.loads(rs.blpop('auth_session')[1]))
            executor.submit(deal_task, task)


def refresh_session(uname, ws_id):
    """
    刷新session
    :param uname
    :param ws_id
    :return:
    """
    rs = redis.Redis(connection_pool=redis_pool)
    rs.delete("{}:{}".format(uname, ws_id))