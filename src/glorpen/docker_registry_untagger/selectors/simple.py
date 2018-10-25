'''
Created on 18 wrz 2018

@author: glorpen
'''
import re
from collections import OrderedDict
from natsort import natsorted
import glorpen.docker_registry_untagger.selectors.base as base
import glorpen.config.fields as fields

class MaxSelector(base.BaseSelector):
    max_items = None
    
    def _setup(self, max_items=None, **kwargs):
        super(MaxSelector, self)._setup(**kwargs)
        self.max_items = max_items
    
    def select(self, tags):
        if self.max_items is None:
            return tags, []
        
        return tags[0:self.max_items], []
    
    @classmethod
    def get_config_fields(cls):
        return {
            "max_items": fields.Number(allow_blank=True)
        }

class PatternSelectorConfig(base.BaseSelectorConfig):
    def _parse_config(self, config):
        self.patterns = self._get_patterns(config)
    
    def _get_patterns(self, patterns):
        ret = {}
        for k,v in patterns.items():
            ps = []
            
            if isinstance(v, dict):
                for ik, iv in v.items():
                    ps.append((re.compile(ik), iv))
            else:
                for i in base.flatten(v):
                    ps.append((re.compile(i), None))
            
            ret[k] = tuple(ps)

        return ret
    
    @classmethod
    def get_config_fields(cls):
        return fields.Dict(
            values=fields.Variant([
                fields.String(),
                fields.List(fields.String()),
                fields.Dict(
                    values=fields.String()
                ),
            ])
        )
    
class PatternSelector(MaxSelector):
    
    def _slice(self, tags, max_items=None):
        if max_items is not None:
            tags[:] = tags[0:max_items]

    def match(self, text):
        for rp, rr in self.patterns:
            m = rp.match(text)
            if m:
                if rr:
                    s = rp.sub(rr, text)
                    return s
                else:
                    return None
        return False
    
    def _setup(self, pattern, **kwargs):
        self.patterns = self._config.patterns[pattern]
        
        super(PatternSelector, self)._setup(**kwargs)
    
    def select(self, tags):
        selected = OrderedDict()
        unmatched = []

        for t in tags:
            ret = self.match(t)
            if ret is False:
                unmatched.append(t)
            else:
                selected[t] = ret
        
        s = natsorted(selected.items(), key=lambda x: x[1], reverse=True)
        s = [i[0] for i in s]
        s, _dummy = super(PatternSelector, self).select(s)
        
        return s, unmatched
    
    @classmethod
    def get_config_fields(cls):
        ret = {}
        ret.update(super(PatternSelector, cls).get_config_fields())
        ret.update({
            'pattern': fields.String()
        })
        return ret

def register(factory):
    factory.add_selector_config(PatternSelectorConfig, "patterns")
    factory.add_selector(MaxSelector, "max")
    factory.add_selector(PatternSelector, "pattern", PatternSelectorConfig)
