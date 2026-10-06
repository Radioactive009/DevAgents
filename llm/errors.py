class LLMError(Exception):
    pass

class LLMAuthenticationError(LLMError):
    pass

class LLMRateLimitError(LLMError):
    pass

class LLMTimeoutError(LLMError):
    pass

class LLMAPIError(LLMError):
    pass

class LLMMalformedResponseError(LLMError):
    pass
    
class LLMConfigurationError(LLMError):
    pass
