class StepError(Exception):
    pass


class StepNoReturnAllowed(StepError):
    pass


class StepOutputMustExist(StepError):
    pass


class StepUndefinedOutput(StepError):
    pass


class InvalidMetadata(Exception):
    pass


class InvalidFingerprint(Exception):
    pass
