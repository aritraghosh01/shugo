class ShugoError(Exception):
    pass


class PolicyError(ShugoError):
    pass


class UpstreamError(ShugoError):
    pass


class AuditError(ShugoError):
    pass


class ApprovalError(ShugoError):
    pass
