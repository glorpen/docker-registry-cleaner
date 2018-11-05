'''
.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
'''
import semver
from glorpen.docker_registry_untagger.selectors.simple import MaxSelector
from py_expression_eval import Parser as ExpressionParser
import glorpen.config.fields as fields
import glorpen.config.exceptions as config_exceptions
from collections import OrderedDict
import itertools

exp_parser = ExpressionParser()

class Expression(object):
    def __init__(self, value=None, min=None, max=None):
        super(Expression, self).__init__()
        
        self._value = value
        self._min = min
        self._max = max
        
    def get_filter(self, **kwargs):
        if self._min or self._max:
            l_min = self._min.evaluate(kwargs) if self._min else None
            l_max = self._max.evaluate(kwargs) if self._max else None
            
            return lambda x: (l_min is None or x>=l_min) and (l_max is None or x<=l_max)
        
        if self._value:
            v = self._value.evaluate(kwargs)
            return lambda x: x == v
        
        return lambda x: True

class ConfigExpressionField(fields.Variant):
    def __init__(self, **kwargs):
        schema = [
            fields.Dict({
                "min": fields.Any(allow_blank=True),
                "max": fields.Any(allow_blank=True)
            }),
            fields.Any(allow_blank=True),
        ]
        super(ConfigExpressionField, self).__init__(schema, **kwargs)
    
    def make_resolvable(self, r):
        super(ConfigExpressionField, self).make_resolvable(r)
        r.on_resolve(self.exp_normalize)
    
    def _parse_expression(self, exp):
        if exp is None:
            return None
        try:
            return exp_parser.parse(str(exp))
        except Exception as e:
            raise config_exceptions.ValidationError("Invalid expression: %r, %s" % (exp, e)) from e
    
    def exp_normalize(self, value, config):
        if value is None:
            return Expression(None)
        
        if isinstance(value, dict):
            return Expression(
                min = self._parse_expression(fields.resolve(value['min'], config)),
                max = self._parse_expression(fields.resolve(value['max'], config))
            )
        else:
            return Expression(self._parse_expression(fields.resolve(value, config)))

class SemVerSelector(MaxSelector):
    
    _ver_keys = ('major', 'minor', 'patch')
    
    def _setup(self, groups, **kwargs):
        super(SemVerSelector, self)._setup(**kwargs)
        
        self._groups = [];
        
        for name, g_conf in groups.items():
            self._setup_group(name, **g_conf)
        
    def _setup_group(self, name, where, preserve, max_items=None):
        self._groups.append((name, where, preserve, max_items))
        #prep_where = self._prepare_group_where(**where)
        #prep_preserve = self._prepare_group_preserve(**preserve)
    
    def _prepare_group_where(self, major=None, minor=None, patch=None, build=None):
        pass
    
    def _prepare_group_preserve(self, major=None, minor=None, patch=None, build=None):
        pass
    
    def _get_where_filters(self, where, latest_ver):
        where_filters = {}
        for pos, exp in where.items():
            latest = getattr(latest_ver, pos) or 0
            f = exp.get_filter(latest=latest)
            where_filters[pos] = f
        
        return where_filters
    
    def _are_where_filters_matched(self, where_filters, version):
        for k,f in where_filters.items():
            if not f(getattr(version, k) or 0):
                return False
        return True
    
    def _group_versions_by_keys(self, versions, offset):
        def _worker(x):
            values = []
            for k in self._ver_keys[0:offset+1]:
                values.append(str(getattr(x, k) or 0))
            
            return ".".join(values)
        
        return itertools.groupby(versions, _worker)
    
    def _split_versions(self, real_versions):
        
        selected = []
        
        if real_versions:
            grouped_versions = OrderedDict((k,tuple(v)) for k,v in self._group_versions_by_keys(real_versions, len(self._ver_keys)-1))
            versions = [semver.VersionInfo.parse(v) for v in grouped_versions.keys()]
            free_versions = set(versions)
            
            latest_ver = max(versions)
            self.logger.debug("detected latest version: %s", latest_ver)
            
            for name, where, preserve, max_items in self._groups:
                self.logger.debug("Searching for %s", name)
                where_filters = self._get_where_filters(where, latest_ver)
                
                matched = set()
                for v in free_versions:
                    if self._are_where_filters_matched(where_filters, v):
                        matched.add(v)
                        self.logger.debug("Matched %s", v)
                
                free_versions.difference_update(matched)
                
                matched = OrderedDict((str(i),i) for i in sorted(matched, reverse=True))
                
                for i, k in enumerate(self._ver_keys):
                    
                    k_preserve = preserve[k]
                    if k_preserve is None:
                        continue
                    
                    # versions with different build metadata should be counted as one
                    grouped = self._group_versions_by_keys(list(matched.values()), i-1)
                    
                    for _group_key, items in grouped:
                        items = list(items)
                        for i in items:
                            del matched[str(i)]
                        for i in items[:k_preserve]:
                            self.logger.debug("Selected %s", i)
                            selected.extend(grouped_versions[str(i)])
            
        return [str(i) for i in set(selected)]
    
    def select(self, tags):
        unmatched = []
        selected = []
        
        for t in tags:
            try:
                v = semver.VersionInfo.parse(t)
            except ValueError:
                unmatched.append(t)
                continue
            
            selected.append(v)
        
        versions = sorted(selected)
        return self._split_versions(versions), unmatched
    
    @classmethod
    def get_config_fields(cls):
        ret = super(SemVerSelector, cls).get_config_fields()
        
        ret.update({
            "groups": fields.Dict(
                values=fields.Dict({
                    "where": fields.Dict({
                        "major": ConfigExpressionField(),
                        "minor": ConfigExpressionField(),
                        "patch": ConfigExpressionField(),
                    }),
                    "preserve": fields.Dict({
                        "major": fields.Number(allow_blank=True),
                        "minor": fields.Number(allow_blank=True),
                        "patch": fields.Number(allow_blank=True),
                    }),
                    "max_items": fields.Number(allow_blank=True),
                })
            )
        })
        return ret

def register(factory):
    factory.add_selector(SemVerSelector, "semver")
