'''
Created on 22 wrz 2018

@author: glorpen
'''

def flatten(items):
    for i in items:
        if isinstance(i, (list, tuple)):
            yield from flatten(i)
        else:
            yield i

class BaseSelector(object):
    def __init__(self, runtime_config, config=None):
        super(BaseSelector, self).__init__()
        
        self._config = config
        self._setup(**runtime_config)
    
    def select(self, tags):
        #return [], tags
        raise NotImplementedError()
    
    def _setup(self, **kwargs):
        if kwargs:
            raise Exception("Unused arguments %r" % list(kwargs.keys()))
    
    @classmethod
    def get_config_fields(cls):
        return {}

class BaseSelectorConfig(object):
    def __init__(self, config):
        super(BaseSelectorConfig, self).__init__()
        
        self._parse_config(config)
    
    @classmethod
    def get_config_fields(cls):
        return {}
