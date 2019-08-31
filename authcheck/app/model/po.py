import re
import datetime
from mongoengine import *
from mongoengine.base import BaseField


# ================================= ↓ example sso ↓ ========================================
class SsoAccount(Document):
    STATUS_VALID = 'valid'
    STATUS_INVALID = 'invalid'

    username = StringField(required=True)
    password = StringField(required=True)
    describe = StringField()
    status = StringField(required=True, default='valid')

    meta = {'collection': 'sso_account'}


class WorkspaceSso(Document):
    """
    自动认证sso所需要的一些信息
    本示例比较简单，实际上只用首页地址即可
    """
    ws_id = ObjectIdField(required=True)
    roles = DictField()
    portal_site = StringField()
    redirect_url = StringField()

    meta = {'collection': 'workspace_sso'}


# ================================= ↓ direct ↓ ========================================
class AuthInfo(EmbeddedDocument):
    """
    认证信息（WorkspaceAuth.auth_info)
    """
    describe = StringField(required=True)
    url_pattern = StringField(required=True)
    auth_header = DictField()
    auth_param = DictField()
    auth_args = DictField()


class WorkspaceAuth(Document):
    ws_id = ObjectIdField(required=True)
    auth_info = ListField(EmbeddedDocumentField(AuthInfo))

    meta = {'collection': 'workspace_auth'}


# ================================= ↓ 工作空间 ↓ ========================================
class Workspace(Document):
    STATUS_INIT = 'init'
    STATUS_START = 'start'
    STATUS_STOP = 'stop'
    STATUS_FINISH = 'finish'

    TYPE_SSO = 'sso'  # 示例sso
    TYPE_DIRECT = 'direct'  # 手动录入信息

    """
    工作空间
    """
    ctime = DateTimeField(default=datetime.datetime.utcnow)
    cname = StringField(required=True)
    status = StringField(required=True, default='init')
    depart_name = StringField()
    system_name = StringField()
    system_type = StringField()
    hosts = ListField(StringField())

    meta = {'collection': 'workspace'}

    @staticmethod
    def ws_status():
        """
        返回工作空间状态
        :return:
        """
        return {i: Workspace.__dict__[i] for i in Workspace.__dict__ if str(i).startswith("STATUS_")}

    @staticmethod
    def sys_types():
        """
        返回系统类型
        :return:
        """
        return {i: Workspace.__dict__[i] for i in Workspace.__dict__ if str(i).startswith("TYPE_")}


# ================================= ↓ 数据包 ↓ ========================================
class Request(EmbeddedDocument):
    """
    请求包
    """
    url = StringField(required=True)
    method = StringField(required=True)
    header = DictField()
    body_content = BaseField()  # 请求体
    body_type = StringField()  # 请求头类型：json/form/xml/bytes (若为bytes类型，则在base64编码后存储)


class Response(EmbeddedDocument):
    """
    响应包
    """
    status_code = IntField(required=True)
    header = DictField()
    body_content = BaseField()
    body_type = StringField()  # 与request相同


class PacketData(Document):
    """
    数据包(PacketRecord.raw_packet / PacketRecord.per_packets)
    """
    banner = StringField(required=True)
    role_describe = StringField(required=True)
    request = EmbeddedDocumentField(Request)
    response = EmbeddedDocumentField(Response)

    meta = {'collection': 'packet_data'}

    @staticmethod
    def raw_query(banner, nor_banner):
        banner = [i.strip() for i in str(banner).split("|") if i.strip() != '']
        nor_banner = [i.strip() for i in str(nor_banner).split("|") if i.strip() != '']
        raw = {
            '$where': """function(){{
                var flag = false;
                if ({}.length == 0){{
                    flag = true;
                }}else{{
                    for(i in {}){{
                        if(this.banner.includes({}[i])){{
                            flag = true;
                            break;
                        }}
                    }}
                }}
                if (flag && {}.length > 0){{
                    for(i in {}){{
                        if(this.banner.includes({}[i])){{
                            flag = false;
                            break;
                        }}
                    }}
                }}
                return flag;
            }}""".format(banner, banner, banner, nor_banner, nor_banner, nor_banner)
        }
        return raw


class PacketRecord(Document):
    """
    流量包
    """
    ws_id = ObjectIdField(required=True)
    username = StringField(required=True)  # 标识用户身份
    ctime = DateTimeField(default=datetime.datetime.utcnow)
    is_delete = BooleanField(default=False)  # 删除标识

    raw_packet = ReferenceField(PacketData)
    per_packets = ListField(ReferenceField(PacketData))

    meta = {'collection': 'packet_record'}

# ================================= ↑ 数据包 ↑ ========================================


if __name__ == '__main__':
    account = SsoAccount()
    account.username = '-'
    account.describe = '空'
    account.save()
