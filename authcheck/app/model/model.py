# coding=utf-8

import re
import base64
import copy
import json
import time
import requests
from enum import Enum
from app.conf.conf import timeout, proxies
from app.model import BasicModel
from app.model.po import *
from app.model.exception import ParserException
from json.decoder import JSONDecodeError
from functools import partial


# policy
class PolicyEnum(Enum):
    """
    权限枚举
    """
    ACCESS = 'access_granted'
    MANAGE = 'manage_granted'


class HeaderModel(object):
    METHOD_PUT = "PUT"
    METHOD_GET = "GET"
    METHOD_POST = "POST"
    METHOD_HEAD = "HEAD"
    METHOD_DELETE = "DELETE"

    def __init__(self, header: dict, status_code: int = None, url: str = None, method: str = None, **kwargs):
        """
        请求/响应 头
        :param url: url,包括get请求的参数（ep: https://xxx.xxx.xxx/uri?param=1）
        :param method: HeaderModel.METHOD_*
        :param status_code: 响应头状态码
        :param header: dcit（正常的header）
        :param kwargs:
        """
        super().__init__(**kwargs)
        method = method.upper()
        assert method in [HeaderModel.METHOD_DELETE, HeaderModel.METHOD_GET, HeaderModel.METHOD_HEAD,
                          HeaderModel.METHOD_POST, HeaderModel.METHOD_PUT]
        self.url = url
        self.method = method
        self.status_code = status_code

        assert isinstance(header, dict)
        self.header = header

    def update_cookie(self, kv: dict):
        """
        更新cookie
        :param kv: dict
        :return:
        """
        cookie = self.header['Cookie']
        if not cookie:
            cookie = ""
        for k, v in kv.items():
            if len(cookie.strip()) == 0:
                cookie = "{}={}".format(k, v)
                continue
            if '{}='.format(k) in cookie:
                cookie = re.sub(r'({}=).*?(;)'.format(k), r'\g<1>{}\g<2>'.format(v),
                                "{};".format(cookie)).strip(";")
                continue
            cookie = "{};{}={}".format(cookie, k, v)
        self.header['Cookie'] = cookie

    def update_headers(self, kv: dict):
        self.header.update(kv)

    def update_args(self, kv: dict):
        """
        更新参数(url中的get参数）
        :param kv: dict
        :return:
        """
        if not kv:
            return
        if not self.url:
            raise ParserException("url为空！")
        for k, v in kv.items():
            if "?" not in self.url:  # url本身没有带着参数的情况
                self.url = "{}?{}={}".format(self.url, k, v)
                continue
            if "{}=".format(k) in self.url:
                self.url = re.sub(r'({}=).*?(&)'.format(k), r'\g<1>{}\g<2>'.format(v),
                                  "{}&".format(self.url)).strip("&")
            else:
                self.url += "&{}={}".format(k, v)


class BodyModel(object):
    TYPE_BYTE = "byte"
    TYPE_JSON = "json"
    TYPE_XML = "xml"
    TYPE_FORM = "form"

    def __init__(self, content="", charset='utf-8', **kwargs):
        """
        请求体
        :param content: 请求体原始内容
        :param charset: 使用的编码
        :param kwargs:
        """
        super().__init__(**kwargs)
        if not charset:
            charset = 'utf-8'
        if isinstance(content, bytes):  # body -> bytes
            try:
                content = content.decode(charset)
            except UnicodeDecodeError:
                self.content = base64.b64encode(content).decode(charset)
                self.type = BodyModel.TYPE_BYTE  # 使用原始字节

        if isinstance(content, str):  # body -> str
            try:
                self.content = json.loads(content)  # json格式
                self.type = BodyModel.TYPE_JSON
            except JSONDecodeError:
                self.content = content.strip()  # 字符串（还应该有xml格式的解析）
                self.type = BodyModel.TYPE_FORM

    def update_param(self, kv: dict):
        """
        根据kv（dict）来设置对应的值
        :param kv: dict
        :return:
        """
        if not kv:
            return
        if self.type == BodyModel.TYPE_JSON:
            assert isinstance(self.content, dict)
            self.content.update(kv)
        elif self.type == BodyModel.TYPE_FORM:
            assert isinstance(self.content, str)
            for k, v in kv.items():
                if "{}=".format(k) in self.content:  # 替换
                    self.content = re.sub(r'({}=).*?(&)'.format(k), r'\g<1>{}\g<2>'.format(v),
                                          "{}&".format(self.content)).strip("&")
                else:  # 当前content中没有这个key，则直接在后面添加即可
                    self.content += "&{}={}".format(k, v)
        else:
            raise ParserException("目前只支持json、form格式")

    def body(self):
        """
        type -> bytes ,返回 bytes
        type -> json , 返回 dict
        :return:
        """
        if self.type == "byte":
            return base64.b64decode(self.content)
        return self.content


class Resp(BasicModel):
    SUCCESS = 'success'
    ERROR = 'error'
    """
    通用的相应包
    """

    def __init__(self, flag, data="操作成功", **kwargs):
        super().__init__(**kwargs)
        assert flag in [Resp.SUCCESS, Resp.ERROR]
        self.flag = flag
        self.data = data


# ====================================== ↓ 请求相关 ↓ ==========================================
class AuthSession(BasicModel):
    def __init__(self, session: requests.Session, account: SsoAccount, **kwargs):
        """
        存储session认证信息
        :param session: requests.session
        :param account: 这个session所属的角色 SsoAccount
        """
        super().__init__(**kwargs)
        self.session = session
        self.account = account

    def request(self, *args, **kwargs):
        return self.session.request(*args, proxies=proxies, verify=False, allow_redirects=False, timeout=timeout,
                                    **kwargs)

    def request_post(self, *args, **kwargs):
        return self.session.post(*args, proxies=proxies, verify=False, allow_redirects=False, timeout=timeout, **kwargs)

    def request_get(self, *args, **kwargs):
        return self.session.get(*args, proxies=proxies, verify=False, allow_redirects=False, timeout=timeout, **kwargs)


requests_request = partial(requests.request, proxies=proxies, verify=False, allow_redirects=False, timeout=timeout)


# ====================================== ↓ 扫描队列model ↓ ==========================================
class TaskModel(BasicModel):
    def __init__(self, name=None, url=None, raw=None, **kwargs):
        """
        扫描目标的实体model
        :param name: 流量所属人
        :param url: 请求url
        :param raw: 原始请求base64编码后
        """
        super().__init__(**kwargs)
        self.name = name
        self.url = url
        self.raw = raw

# ====================================== ↑ 扫描队列model ↑ ==========================================
