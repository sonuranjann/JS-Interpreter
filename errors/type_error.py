class JSTypeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"TypeError: {message}")
