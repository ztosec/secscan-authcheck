import re
import os
import json
import time
import pickle
from app.conf.conf import *
from app.model.model import *
from app.model.exception import *
from flask import request, render_template
from mongoengine import Document


def validate_url(u: str):
    """
    校验url是否有效
    :param u:
    :return:
    """
    if not re.match(r'^http[s]?://\S+$', u):
        return False
    return True


def parse_params(args: str):
    """
    解析参数
    :param args: aa=1&bb=2&cc=3
    :return: {}
    """
    ps = {}
    for kv in args.split('&'):
        _kv = str(kv).split('=', 1)
        if len(_kv) < 2:
            continue
        k, v = _kv
        ps[k] = v
    return ps


def parse_url_params(url: str):
    """
    获取url中的参数
    :param url:
    :return: path, raw_params, {
        'param1': param1,
        'param2': param2
    }
    """
    if '?' not in url:
        return url, None, None
    path, raw_params = url.split('?', 1)
    return path, raw_params, parse_params(raw_params)


def get_page(page: int, size: int, total: int):
    """
    分页用
    :param page: 当前页数（从0开始）
    :param size: 页大小
    :param total: 数据总量
    :return:
    """
    if total == 0:
        return {
            'dic': ["0"]
        }
    max_page = int(total / size) if total % size != 0 else int(total / size) - 1
    per_page = False if page == 0 else page - 1
    next_page = False if page == max_page else page + 1

    # 前2后3
    dic = [i for i in range(page - 2, page + 4) if (0 <= i <= max_page)]

    # 省略号
    per_ellipsis = True if dic[0] > 1 else False
    suf_ellipsis = True if dic[-1] < (max_page - 1) else False

    # 最后一个和最前一个
    p_min = "0" if dic[0] > 0 else False
    p_max = max_page if dic[-1] < max_page else False

    return {
        'per_page': per_page,
        'next_page': next_page,
        'dic': dic,
        'per_ellipsis': per_ellipsis,
        'suf_ellipsis': suf_ellipsis,
        'p_min': p_min,
        'p_max': p_max
    }


def deal_header(url: str, content: bytes, charset='utf-8') -> HeaderModel:
    content = content.decode(charset)

    lines = content.split('\n', 1)
    assert len(lines) > 1

    groups = space_pattern.split(lines[0])
    assert len(groups) > 2  # e.g: GET /uri HTTP/1.1
    method = groups[0]

    lines = lines[1].splitlines()
    header = {}
    for line in lines:
        lr = line.split(":", 1)
        if len(lr) != 2:
            continue
        header[lr[0].strip()] = lr[1].strip()

    return HeaderModel(url=url, method=method, header=header)


def deal_body(content: bytes, charset='utf-8') -> BodyModel:
    return BodyModel(content, charset=charset)


def gen_banner(role, method, url, response_content) -> str:
    """
    生成banner用来展示
    :return:
    """
    banner = "{}  -  {}({})  -  {}  -  {}"
    return banner.format(str(role)[:8], str(method)[:8], len(str(response_content)), str(url)[:100],
                         str(response_content)[:150])


def resp_length(banner: str):
    """
    获取banner中的响应包长度
    :param banner:
    :return:
    """
    if not banner:
        return 0
    try:
        left = banner.index('(')
        right = banner.index(')')

        length = int(banner[left + 1: right])
    except ValueError:
        return 0
    return length


def deal_request(url, raw) -> (HeaderModel, BodyModel):
    """
    处理请求
    :param url: url
    :param raw: 原生的请求的base64编码，包括请求头、请求体
    :return:
    """
    try:
        raw = base64.b64decode(raw)
    except Exception as e:
        raise LibException(e)

    f = raw.find(b'\r\n\r\n')  # 正常应该是这个，但是可能有特殊情况（比如自己手动输入）可能会是下面的那个
    if f < 0:
        f = raw.find(b'\n\n')
    if f < 0:
        header = raw.strip()
        body = b''
    else:
        header = raw[: f].strip()
        body = raw[f:].strip()

    matches = re.findall(rb'charset=(.*?)[\s;]', header)
    if len(matches) != 0:
        charset = matches[0].decode('utf-8')
    else:
        charset = encoding
    try:
        r_header = deal_header(url, header, charset=charset)
        r_body = deal_body(body, charset=charset)
    except Exception as e:
        raise ParserException(e)
    return r_header, r_body


def to_json(doc: Document):
    if isinstance(doc, list):
        t = []
        for d in doc:
            t.append(to_json(d))
        return t
    return json.loads(doc.to_json())


__all__ = [
    'validate_url', 'parse_params', 'parse_url_params', 'get_page', 'resp_length',
    'deal_header', 'deal_body', 'gen_banner', 'deal_request', 'to_json'
]

if __name__ == '__main__':
    url = 'http://www.zto.com?a=1&b=2&c=3'
    path, raw_params, params = parse_url_params(url)
    print(path)
    print(raw_params)
    print(params)
