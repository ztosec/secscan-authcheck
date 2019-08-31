class WebException(Exception):
    pass


class ParserException(Exception):
    """
    解析异常
    """
    pass


class ApiException(Exception):
    """
    api异常
    """
    pass


class WsException(Exception):
    """
    轮询异常
    """
    pass


class SsoException(Exception):
    """
    sso异常
    """
    pass


class LibException(Exception):
    """
    lib异常
    """
    pass


class AccountException(Exception):
    """
    账号异常（账号失效）
    """
    pass


class FlowException(Exception):
    """
    认证流量异常
    """
    pass
