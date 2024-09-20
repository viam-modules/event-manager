class Action():
    resource: str
    method: str
    payload: str
    when_secs: int
    sms_match: str = ""
    taken: bool = False
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value