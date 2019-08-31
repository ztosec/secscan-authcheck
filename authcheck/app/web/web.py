import redis
from app import redis_pool
from app.model.exception import *
from app.common.decorators import *
from flask import request, make_response, redirect
from app.web import bp_web
from app.core.lib import refresh_session
from app.common.func import is_manager
from app.common.util import get_page, resp_length
from app.conf.conf import *
from app.model.po import *
from app.model.model import PolicyEnum


@bp_web.route("/favicon.ico")
def favicon():
    """
    favicon
    :return:
    """
    from app import app_path
    resp = make_response()
    resp.headers['Content-Type'] = 'image/x-icon'
    with open(os.path.join(app_path, "..", "favicon.ico"), "rb") as f:
        resp.set_data(f.read())
    return resp


@bp_web.route("/welcome")
@login_check
@templated("welcome.html")
def welcome():
    rs = redis.Redis(connection_pool=redis_pool)
    statistics = rs.hgetall("statistics")
    if not statistics:
        ws_num = Workspace.objects.count()
        request_num = PacketRecord.objects.count()

        people_set = set()
        depart_set = set()
        system_set = set()
        hosts_set = set()
        for ws in Workspace.objects():
            depart_set.add(ws.depart_name)
            system_set.add(ws.system_name)
            hosts_set.update(ws.hosts)
        for pr in PacketRecord.objects():
            people_set.add(pr.username)

        statistics = {
            "ws_num": ws_num,
            "request_num": request_num,
            "people_num": len(people_set),
            "depart_num": len(depart_set),
            "system_num": len(system_set),
            "hosts_num": len(hosts_set)
        }
        rs.hmset("statistics", statistics)
        rs.expire("statistics", statistics_timeout * 60)
    else:
        statistics = {k.decode('utf-8'): v.decode('utf-8') for k, v in statistics.items()}
    return statistics


@bp_web.route("/login")
@templated("/login.html")
def login():
    pass


@bp_web.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login"))


@bp_web.route("/")
@login_check
@templated("/home.html")
def home():
    pass


@bp_web.route("/workspace/<_id>", methods=['GET', 'POST'])
@login_check
@templated("/workspace-traffic.html")
def workspace_traffic(_id):
    """
    工作空间内的流量明细
    :return:
    """
    banner = ""
    nor_banner = ""
    al = None
    suspect = None
    if request.method == 'POST':
        banner = request.form.get('banner')
        nor_banner = request.form.get('nor_banner')
        al = request.form.get('al')
        suspect = request.form.get('suspect')

    # 此处不做权限校验，可直接通过这个工作空间id来读取数据，便于分享
    # if not is_manager():
    #     ws = Workspace.objects(id=_id, cname=session['username'])
    #     if len(ws) == 0:
    #         raise NormalException("没有找到对应工作空间")

    # 刷新session
    refresh_session(session.get('username'), _id)

    obj = PacketRecord.objects(ws_id=_id)
    if not al:
        obj = obj.filter(is_delete=False)
    packet_records = obj.order_by('-ctime')

    hits = []
    for pr in packet_records:
        assert isinstance(pr, PacketRecord)

        # raw_packet
        pd = PacketData.objects(id=pr.raw_packet.id,
                                __raw__=PacketData.raw_query(banner, nor_banner))
        if len(pd) == 0:
            pr.raw_packet = None
        else:
            pr.raw_packet = pd[0]

        # per_packets
        pr.per_packets = PacketData.objects(id__in=[i.id for i in pr.per_packets],
                                            __raw__=PacketData.raw_query(banner, nor_banner))
        if not pr.raw_packet or not pr.per_packets:
            continue
        if suspect:  # 只展示可疑的请求
            for pd in pr.per_packets:
                assert isinstance(pd, PacketData)
                if resp_length(pr.raw_packet.banner) == resp_length(pd.banner):
                    hits.append(pr)
                    break
        else:
            hits.append(pr)

    return {
        'banner': banner,
        'nor_banner': nor_banner,
        'workspace_id': _id,
        'packet_records': hits,
        'al': al,
        'suspect': suspect
    }


# =================================== ↓ 工作空间 ↓ =============================================
@bp_web.route("/workspace", methods=['GET', 'POST'])
@login_check
@templated("/workspace.html")
def workspace():
    page = int(request.args.get('page')) if request.args.get('page') else 0
    size = int(request.args.get('size')) if request.args.get('size') else 50
    form = request.form

    raw = {}
    if form.get('cname'):
        raw['cname'] = form.get('cname')
    if form.get('status'):
        raw['status'] = form.get('status')
    if form.get('depart_name'):
        raw['depart_name'] = {
            '$regex': form.get('depart_name')
        }
    if form.get('system_name'):
        raw['system_name'] = {
            '$regex': form.get('system_name')
        }
    if not is_manager():
        raw['cname'] = session['username']

    objects = Workspace.objects(__raw__=raw).order_by('-ctime')
    count = objects.count()
    hits = objects[page * size: page * size + size]

    return {
        'form': form,
        'page': page,
        'size': size,
        'count': count,
        'hits': hits,
        'hit': get_page(page, size, count)
    }


@bp_web.route("/workspace-create")
@login_check
@templated("/workspace-create.html")
def workspace_create():
    return {
        'source': {}
    }


@bp_web.route("/workspace/<_id>/config")
@login_check
@templated("/workspace-config.html")
def workspace_config(_id):
    return {
        'ws_id': _id
    }


# =================================== ↑ 工作空间 ↑ =============================================


# =================================== ↓ role ↓ ================================================
@bp_web.route("/account")
@login_check
@templated("/sso-account.html")
def sso_account():
    return {'hits': SsoAccount.objects()}


@bp_web.route("/account-add")
@policy_check(PolicyEnum.MANAGE)
@templated("/sso-account-edit.html")
def sso_account_add():
    return {'account': {}}


@bp_web.route("/account/edit/<_id>")
@policy_check(PolicyEnum.MANAGE)
@templated("/sso-account-edit.html")
def sso_account_edit(_id):
    account = SsoAccount.objects(id=_id)
    if len(account) == 0:
        raise ApiException("account {} not found!".format(_id))
    account = account[0]
    return {
        'account': account
    }


@bp_web.route("/account/show/<_id>")
@policy_check(PolicyEnum.MANAGE)
@templated("/sso-account-show.html")
def sso_account_show(_id):
    account = SsoAccount.objects(id=_id)
    if len(account) == 0:
        raise ApiException("account {} not found!".format(_id))
    account = account[0]
    return {
        'account': account
    }
# =================================== ↑ account ↑ =============================================
