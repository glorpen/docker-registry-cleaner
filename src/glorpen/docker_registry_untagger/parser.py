'''
Created on 18 wrz 2018

@author: glorpen
'''
import glorpen.config as config
import glorpen.config.fields as fields
import glorpen.config.loaders as loaders
from pprint import pprint

class RepoConfigField(fields.Field):
    
    def __init__(self, schemas, **kwargs):
        super(RepoConfigField, self).__init__()
        
        self._schemas = schemas
    
    def make_resolvable(self, r):
        r.on_resolve(self.normalize)
    
    def is_value_supported(self, value):
        return isinstance(value, (dict,))
    
    def normalize(self, value, config):
        type_ = value.pop("type")
        try:
            s = self._schemas[type_]
        except KeyError:
            raise Exception('Unknown schema name %r, available: %r' % (type_, tuple(self._schemas.keys())))
        
        return [type_, s.resolve(value)]

class Loader(object):
    def __init__(self, path):
        super(Loader, self).__init__()
        
        self.path = path
        self.data = None
        
        self._selector_configs_schemas = {}
        self._selector_schemas = {}
    
    def _get_schema(self):
        return fields.Dict({
                "accounts": fields.Dict(
                    values=fields.Dict({
                        "auth": fields.Dict({
                            "user": fields.String(allow_blank=True),
                            "password": fields.String(allow_blank=True)
                        })
                    })
                ),
                "repositories": fields.Dict(
                    values=fields.Dict(
                        keys=fields.String(),
                        values=RepoConfigField(self._selector_schemas)
                    )
                ),
                **self._selector_configs_schemas
        })

    
    def load(self):
        cfg = config.Config(
            loader=loaders.YamlLoader(filepath=self.path),
            spec=self._get_schema()
        ).finalize()
        
        self.data = cfg.data
    
    def add_selector_schema(self, type_name, schema):
        self._selector_schemas[type_name] = fields.Dict(schema)
    
    def add_selector_config_schema(self, config_key, schema):
        self._selector_configs_schemas[config_key] = schema
