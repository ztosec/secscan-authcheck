import uuid
from app import users
from app.core.identify.sso import sso_account_record
from app.web import bp_api
from app.common.decorators import *
from app.core.lib import *
from app.common.func import is_manager, format_request, format_response
from app.model.exception import *
from app.common.util import *
from flask import request, jsonify, session
from app.core.flow import watch_hosts


@bp_api.route("/watch", methods=['POST'])
@login_check
def site_parse():
    data = request.get_json()
    if not data:
        raise ApiException('Incorrect format!')

    if not data.get('site'):
        raise ApiException('请输入有效的站点！')
    current_url, system_type, hs, portal_site = watch_hosts(data['site'])

    return jsonify(Resp(Resp.SUCCESS, {
        'redirect_url': current_url,
        'system_type': system_type,
        'hs': ','.join(hs),
        'portal_site': portal_site,
    }))


@bp_api.route("/identify")
@login_check
def identify():
    """
    为该session中的唯一用户名生成一个唯一标识（每次都会重新标识）
    后面可通过该标识获取当前用户
    :return: [username, uid]
    """
    username = session.get('username')
    rs = redis.Redis(connection_pool=redis_pool)

    uid = uuid.uuid1().hex
    rs.hset("user_identify", username, uid)

    return jsonify(Resp(Resp.SUCCESS, [username, uid]))


@bp_api.route("/login", methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        raise ApiException("请求格式错误")

    user = users.get(data['username'])
    if not user or user.get('password') != data.get('password'):
        raise ApiException("账号或密码错误")
    session['username'] = data['username']
    session['role'] = user.get('role')
    return jsonify(Resp(Resp.SUCCESS))


@bp_api.route("/logout")
def logout():
    session.clear()
    return jsonify(Resp(Resp.SUCCESS))


@bp_api.route("/parse", methods=['POST'])
def req_parse():
    """
    接收请求，把要扫描的内容推入队列中
    :return:
    """
    uid = request.form.get('uid')  # 流量的所属人
    url = request.form.get('url')
    raw = request.form.get('raw')

    rs = redis.Redis(connection_pool=redis_pool)
    name = None
    for k, v in rs.hscan_iter("user_identify"):
        if v.decode('utf-8') == uid:
            name = k.decode('utf-8')
            break

    if not name:
        raise ApiException('identify error')
    logger.debug("parse {} {}".format(name, url))

    task = TaskModel(name, url, raw)
    rs.rpush("auth_session", json.dumps(task))

    return jsonify(Resp(Resp.SUCCESS))


# --------------------------- ↓ 流量 ↓-------------------------------------
@bp_api.route("/packetdata/<pd_id>")
@login_check
def packet_data(pd_id):
    """
    获取一个数据包的信息
    :param pd_id:
    :return:
    """
    pd = PacketData.objects(id=pd_id)
    if len(pd) != 1:
        raise ApiException("错误的数据包id: ".format(pd_id))
    pd = pd[0]
    assert isinstance(pd, PacketData)

    return jsonify(Resp(Resp.SUCCESS, {
        'banner': pd.banner,
        'describe': pd.role_describe,
        'req': format_request(pd.request),
        'resp': format_response(pd.response)
    }))


@bp_api.route("/replay/<pr_id>")
@login_check
def replay_traffic(pr_id):
    """
    流量重放 数据包id
    :param pr_id:
    :return:
    """
    pr = PacketRecord.objects(id=pr_id)
    if len(pr) == 0:
        raise ApiException("{} not found!".format(pr_id))
    pr = pr[0]
    assert isinstance(pr, PacketRecord)

    pr_replay(session.get('username'), pr)

    return jsonify(Resp(Resp.SUCCESS))


# --------------------------- ↑ 流量 ↑-------------------------------------


# --------------------------- ↓ 工作空间 ↓-------------------------------------
@bp_api.route("/workspace", methods=['PUT'])
@login_check
def workspace():
    """
    工作空间
    PUT: (新增）
    :return:
    """
    data = request.get_json()
    if not data:
        raise ApiException('Incorrect format!')

    depart_name = data.get('depart_name')
    system_name = data.get('system_name')

    if not depart_name or not system_name:
        raise ApiException("请输入部门和系统名!")

    ws = Workspace(depart_name=depart_name, cname=session['username'], system_name=system_name)
    ws.save()
    logger.info("workspace created: {}".format(ws.id))

    return jsonify(Resp(Resp.SUCCESS, str(ws.id)))


@bp_api.route("/workspace/<_id>", methods=['GET', 'DELETE'])
@login_check
def workspace_op(_id):
    """
    GET： 查询工作空间信息
    :param _id:
    :return:
    """

    if is_manager():
        ws = Workspace.objects(id=_id)
    else:
        ws = Workspace.objects(id=_id, cname=session['username'])
    if len(ws) == 0:
        raise ApiException("未找到对应的工作空间：".format(_id))
    ws = ws[0]
    assert isinstance(ws, Workspace)

    if request.method == 'GET':
        d = to_json(ws)
        d.update({
            'request_num': PacketRecord.objects(ws_id=_id).count()
        })
        return jsonify(Resp(Resp.SUCCESS, d))
    else:
        PacketRecord.objects(ws_id=ws.id).update(is_delete=True)
        rs = redis.Redis(connection_pool=redis_pool)
        rs.delete("parse_heap:{}:{}".format(session['username'], _id))
        return jsonify(Resp(Resp.SUCCESS))


@bp_api.route("/workspace/<_id>/config", methods=['PUT', 'GET'])
@login_check
def workspace_config(_id):
    """
    PUT: 配置工作空间
    GET: 获取工作空间配置
    :param _id:
    :return:
    """
    if request.method == 'GET':
        if is_manager():
            ws = Workspace.objects(id=_id)
        else:
            ws = Workspace.objects(id=_id, cname=session['username'])
        if len(ws) == 0:
            raise ApiException('未找到对应工作空间：{}'.format(_id))
        ws = ws[0]
        assert isinstance(ws, Workspace)
        data = to_json(ws)

        if ws.system_type == Workspace.TYPE_DIRECT:  # 手动认证
            auth = WorkspaceAuth.objects(ws_id=_id)
            if len(auth) != 0:
                data['roles'] = to_json(auth[0])
            else:
                data['roles'] = None
        else:  # sso认证
            sso = WorkspaceSso.objects(ws_id=_id)
            if len(sso) != 0:
                data['roles'] = to_json(sso[0])
            else:
                data['roles'] = None
        return jsonify(Resp(Resp.SUCCESS, data))

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            raise ApiException("请求不可空！")
        if not is_manager():
            ws = Workspace.objects(id=_id, cname=session['username'])
            if len(ws) == 0:
                raise ApiException("未找到对应工作空间：{}".format(_id))
        conf_workspace(_id, data)
        return jsonify(Resp(Resp.SUCCESS))


# --------------------------- ↓ 角色/账号 ↓------------------------------------
@bp_api.route("/sso/account", methods=['GET', 'PUT'])
@policy_check(PolicyEnum.MANAGE, method='PUT')
def sso_account():
    """
    GET: 获取账号列表
    PUT: 添加账号
    :return:
    """
    if request.method == 'GET':
        accounts = SsoAccount.objects.exclude('password')
        return jsonify(Resp(Resp.SUCCESS, to_json(accounts)))

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            raise ApiException("Incorrect format!")
        try:
            sso_account_record(username=data.get('username'), password=data.get('password'),
                               describe=data.get('describe'))
        except Exception as e:
            raise ApiException(e)

    return jsonify(Resp(Resp.SUCCESS))


@bp_api.route("/sso/account/<_id>", methods=['GET', 'PUT', 'DELETE'])
@policy_check(PolicyEnum.MANAGE)
def sso_account_op(_id):
    """
    GET: 获取该账号明细
    PUT: 修改账号信息
    DELETE: 删除
    :param _id:
    :return:
    """
    if request.method == 'GET':
        account = SsoAccount.objects(id=_id)
        if len(account) == 0:
            raise ApiException("id error!")
        account = account[0]
        return jsonify(Resp(Resp.SUCCESS, to_json(account)))

    if request.method == 'DELETE':
        SsoAccount.objects(id=_id).delete()
        return jsonify(Resp(Resp.SUCCESS))

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            raise ApiException("Incorrect format!")
        username = data.get('username')
        pwd = data.get('password')
        desc = data.get('describe')

        if not username:
            return jsonify(Resp(Resp.ERROR, '请输入用户名'))
        sso_account_record(username, pwd, desc, _id)
        return jsonify(Resp(Resp.SUCCESS))


@bp_api.route("/<_id>/refresh", methods=['DELETE'])
@login_check
def auth_refresh(_id):
    """
    刷新自己工作空间的认证信息
    :param _id: (对应工作空间id）
    :return:
    """
    refresh_session(session.get('username'), _id)
    return jsonify(Resp(Resp.SUCCESS))
