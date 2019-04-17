"""
.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
"""

from glorpen.docker_registry_cleaner.parser import Loader
import glorpen.di as di
import importlib
from glorpen.docker_registry_cleaner import api, native
from collections import OrderedDict
import logging

class SelectorFactory(object):
    def __init__(self):
        super(SelectorFactory, self).__init__()
        self._selectors = {}
    
    def add_selector(self, cls, symbol, config=None):
        self._selectors[symbol] = (cls, config)
    
    def get(self, symbol, kwargs):
        s_cls, config = self._selectors[symbol]
        return s_cls(kwargs, config)

class AppCompositor(object):
    """Wires application components.
    
    Uses :class:`glorpen.di.Container` to define services and args.
    """
    
    registry_address = "127.0.0.1:5000"
    
    def __init__(self, config_path, registry_data, registry_bin):
        """
        :param config_path: Path to config file.
        :type config_path: str
        :param registry_data: Path to registry data dir.
        :type registry_data: str
        :param registry_bin: Path to registry binary.
        :type registry_bin: str
        """
        super(AppCompositor, self).__init__()
        self._c = di.Container()
    
        svc = self._c.add_service(Loader)
        svc.kwargs(path=config_path)
        
        svc = self._c.add_service(SelectorFactory)
        
        svc = self._c.add_service(api.DockerRegistry)
        svc.kwargs(url="http://%s" % self.registry_address)
        
        svc = self._c.add_service("app.cleaners")
        svc.implementation(self._create_cleaners)
        svc.kwargs(loader__svc=Loader, selector_factory__svc=SelectorFactory)
        
        svc = self._c.add_service(Untagger)
        svc.kwargs(registry__svc=api.DockerRegistry, cleaners__svc="app.cleaners")
        
        svc = self._c.add_service(native.RegistryStorage)
        svc.kwargs(registry_path=registry_data)
        
        svc = self._c.add_service(native.NativeRegistry)
        svc.kwargs(registry_data=registry_data, registry_address=self.registry_address, registry_bin=registry_bin)
        
        svc = self._c.add_service(Cleaner)
    
    def add_selector(self, cls, symbol, config_cls=None):
        """Adds new selector type for use in configuration.
        
        :param cls: Selector class.
        :type cls: callable
        :param symbol: Selector symbol used in config.
        :type symbol: str
        :param config_cls: Optional selector configuration class.
        :type config_cls: str
        
        """
        svc = self._c.get_definition(SelectorFactory)
        svc.call("add_selector", cls=cls, symbol=symbol, config__svc=config_cls)
        
        config_schema = cls.get_config_fields()
        
        svc = self._c.get_definition(Loader)
        svc.call('add_selector_schema', type_name=symbol, schema=config_schema)
    
    def create_selector_config(self, cls, loader: Loader, config_key):
        return cls(loader.data.get(config_key))
    
    def add_selector_config(self, cls, config_key=None):
        svc = self._c.add_service(cls)
        svc.factory(callable=self.create_selector_config, loader__svc=Loader, config_key=config_key, cls=cls)
        
        if config_key:
            svc = self._c.get_definition(Loader)
            config_schema = cls.get_config_fields()
            svc.call('add_selector_config_schema', config_key=config_key, schema=config_schema)
    
    def register_module(self, path):
        getattr(importlib.import_module(path), "register")(self)
    
    def _create_cleaners(self, loader, selector_factory: SelectorFactory):
        cleaners = []
        for name, conf in loader.data["repositories"].items():
            types = OrderedDict((k, selector_factory.get(*v)) for k,v in conf["cleaners"].items())
            cleaners.append(api.DockerRepository(name, conf["paths"], types))
        return tuple(cleaners)
    
    def commit(self):
        svc = self._c.get_definition(Loader)
        svc.call("load")
        
        return self._c.get(Cleaner)

class Untagger(object):
    
    fake_tag = "untagger-for-deletion"
    
    def __init__(self, registry, cleaners):
        super(Untagger, self).__init__()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.registry = registry
        self.cleaners = cleaners
    
    def get_supported_cleaner(self, repository):
        for r in self.cleaners:
            if r.supports_repo(repository):
                return r
    
    def delete_tags(self, registry, repo, tags):
        fake_ref = registry.upload_fake_image(repo, self.fake_tag)
        
        for t in tags:
            if t == self.fake_tag:
                continue
            # dont delete, just tag fake image with tags for deletion
            registry.tag(repo, self.fake_tag, t, cache=True)
        
        # will remove _image_ referenced by tag, not just tag
        registry.remove_image(repo, fake_ref)
    
    def clean_repository(self, registry, repo, pretend=False):
        cleaner = self.get_supported_cleaner(repo)
        
        if cleaner:
            tags = registry.get_tags(repo)
            self.logger.info("Using cleaner %r for repo %r", cleaner.name, repo)
            if tags:
                tags_for_deletion = cleaner.select_tags(tags)
                
                if tags_for_deletion:
                    if pretend:
                        for i in tags_for_deletion:
                            self.logger.info("Would delete %s:%s", repo, i)
                    else:
                        self.delete_tags(registry, repo, tags_for_deletion)
                    return True
            else:
                self.logger.info("Found empty repo %s", repo)
        else:
            self.logger.info("Cleaner for %s not found", repo)
        
        return False
    
    def clean(self, pretend=False):
        if not self.registry.check():
            raise Exception('Could not connect to %s' % self.registry)
        
        for repo in self.registry.get_repositories():
            self.clean_repository(self.registry, repo, pretend)
    
    def list_repos(self):
        ret = {}
        for repo in self.registry.get_repositories():
            ret[repo] = self.registry.get_tags(repo)
        return ret
    
    def close(self):
        self.registry.close()

class Cleaner(object):
    def __init__(self, untagger: Untagger, registry_storage: native.RegistryStorage, native_registry: native.NativeRegistry):
        super(Cleaner, self).__init__()
        
        self._untagger = untagger
        self._storage = registry_storage
        self._native = native_registry
    
    def clean(self, pretend=False):
        with self._native.run():
            self._untagger.clean(pretend)
            
        if not pretend:
            self._native.garbage_collect()
            self._storage.remove_repositories_without_tags()
            self._native.garbage_collect()
    
    def close(self):
        self._native.cleanup()
        self._untagger.close()
    
    def list_repos(self):
        with self._native.run():
            return self._untagger.list_repos()
