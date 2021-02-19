class StepError(Exception):
    pass


class NoReturnAllowed(StepError):
    def __init__(self, msg=None, *args, **kwargs):
        default_msg = (
            'Step instructions should not provide any return value.'
            ' All results should be written to the Step output path.'
        )
        # noinspection PyArgumentList
        super().__init__(msg or default_msg, *args, **kwargs)


class OutputMustExist(StepError):
    def __init__(self, msg=None, *args, **kwargs):
        default_msg = (
            'Step instructions must populate all paths defined in output.'
        )
        # noinspection PyArgumentList
        super().__init__(msg or default_msg, *args, **kwargs)
