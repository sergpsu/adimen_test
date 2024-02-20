class AppBaseException(Exception):
    pass


class AlreadyExists(AppBaseException):
    def __str__(self):
        return f"already exists: {self.args[0]}"


class NotFound(AppBaseException):
    def __str__(self):
        return f"not found: {self.args[0]}"
