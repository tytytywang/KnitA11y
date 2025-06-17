class ErrorException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class WarningException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class LogException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)