import pickle
import redis
import uuid
from flask import request, jsonify, session
from app import redis_pool
from app.web import bp_ws
from app.model.po import PacketRecord, PacketData
from app.model.model import Resp
from app.common.util import to_json, resp_length
from app.common.decorators import login_check
from app.model.exception import WsException
from app.conf.conf import logger, listening_timeout


@bp_ws.route("/<ws_id>/listening", methods=['POST'])
@login_check
def listening(ws_id):
    logger.debug("listening start ...")
    data = request.get_json()
    if not data:
        raise WsException("参数错误！")
    rs = redis.Redis(connection_pool=redis_pool)

    uid = uuid.uuid1().hex
    banner = data.get('banner') if isinstance(data.get('banner'), str) else ""
    nor_banner = data.get('nor_banner') if isinstance(data.get('nor_banner'), str) else ""
    suspect = data.get('suspect') if isinstance(data.get('suspect'), str) else ""

    rs.hmset("listening:{}:setting".format(uid), {
        'ws_id': ws_id,
        'name': session.get('username'),
        'banner': banner,
        'nor_banner': nor_banner,
        'suspect': suspect
    })
    rs.expire("listening:{}:setting".format(uid), listening_timeout)

    return jsonify(Resp(Resp.SUCCESS, uid))


def _banner_match(pd_banner: str, matches: str, nor_matches: str):
    if not pd_banner:  # 一般都有值
        return True

    matches = [i.strip() for i in matches.split('|') if i.strip() != '']
    nor_matches = [i.strip() for i in nor_matches.split('|') if i.strip() != '']

    if matches == [""]:
        matches = []
    if nor_matches == [""]:
        nor_matches = []

    flag = False
    if not matches:
        flag = True
    else:
        for match in matches:
            if match in pd_banner:
                flag = True
                break
    if flag and nor_matches:
        for nor_match in nor_matches:
            if nor_match in pd_banner:
                flag = False
                break
    return flag


@bp_ws.route("/polling", methods=['POST'])
def polling():
    rest = request.get_json()
    if not rest:
        raise WsException("参数错误！")
    uid = rest.get('uid')

    rs = redis.Redis(connection_pool=redis_pool)
    setting = rs.hgetall("listening:{}:setting".format(uid))

    if not setting:
        raise WsException("{} not found!".format(uid))
    setting = {k.decode('utf-8'): v.decode('utf-8') for k, v in setting.items()}

    rs.expire("listening:{}".format(uid), listening_timeout * 60)
    rs.expire("listening:{}:setting".format(uid), listening_timeout * 60)

    pr = rs.blpop("listening:{}".format(uid), timeout=7)
    logger.debug("{} found packet_record: {}".format(uid, pr))
    if pr and len(pr) == 2:
        pr = pickle.loads(pr[1])
        assert isinstance(pr, PacketRecord)

        if setting.get('suspect'):  # 只展示可疑请求
            flag = False
            for per in pr.per_packets:
                assert isinstance(per, PacketData)
                if resp_length(pr.raw_packet.banner) == resp_length(per.banner):
                    flag = True
                    break
            if not flag:
                return jsonify(Resp.SUCCESS)

        raw_packet = to_json(pr.raw_packet)
        per_packets = to_json(pr.per_packets)
        pr = to_json(pr)
        pr['raw_packet'] = None

        if _banner_match(raw_packet.get('banner'), setting.get('banner'), setting.get('nor_banner')):
            pr['raw_packet'] = raw_packet
            pr['raw_packet']['request'] = None
            pr['raw_packet']['response'] = None

        pers = []
        for p in per_packets:
            if _banner_match(p.get('banner'), setting.get('banner'), setting.get('nor_banner')):
                pers.append(p)
                p['request'] = None
                p['response'] = None

        pr['per_packets'] = pers if len(pers) > 0 else None

        return jsonify(Resp(Resp.SUCCESS, pr))
    return jsonify(Resp(Resp.SUCCESS))
