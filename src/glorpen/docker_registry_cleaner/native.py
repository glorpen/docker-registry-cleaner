'''
Created on 4 kwi 2019

@author: glorpen
'''
import os
import shutil
import logging
import subprocess
import yaml
import pkg_resources
import contextlib
import threading

class NativeRegistry(object):
    
    config_path = "/tmp/registry-config.yaml"
    registry_proc = None
    
    def __init__(self, registry_data, registry_bin, registry_address):
        super(NativeRegistry, self).__init__()
        
        self.registry_data = registry_data
        self.registry_address = registry_address
        self.registry_bin = registry_bin
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.registry_logger = logging.getLogger("%s:registry" % self.__class__.__name__)
    
    def _save_config(self):
        if not os.path.exists(self.config_path):
            with pkg_resources.resource_stream(__package__, 'resources/registry.yaml') as f:
                d = yaml.safe_load(f)
                
                d["storage"]["filesystem"]["rootdirectory"] = self.registry_data
                d["http"]["addr"] = self.registry_address
                
                with open(self.config_path, "wt") as f:
                    yaml.dump(d, f)
        
        return self.config_path
    
    def cleanup(self):
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    def garbage_collect(self):
        self.logger.info("Running garbage collector")
        p = subprocess.Popen([self.registry_bin, "garbage-collect", self._save_config(), "--delete-untagged=true"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        retval = self._track_process(p, wait=True)
        
        if retval != 0:
            raise Exception("registry garbage-collect failed")
    
    def _track_process(self, p, cb=None, wait=True):
        
        shared_data = {"cb":cb}
        
        def _read(fd):
            for line_raw in fd:
                line = line_raw.decode().strip()
                cb = shared_data["cb"]
                if cb:
                    if cb(line):
                        shared_data["cb"] = None
                self.registry_logger.debug(line)
            fd.close()
        
        threading.Thread(target=_read, kwargs={"fd": p.stderr}, daemon=True).start()
        threading.Thread(target=_read, kwargs={"fd": p.stdout}, daemon=True).start()
        
        if wait:
            return p.wait()
    
    def start(self):
        self._registry_proc = subprocess.Popen([self.registry_bin, "serve", self._save_config()], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        msg = "listening on %s" % self.registry_address
        
        c = threading.Condition()
        
        def daemon_semaphore(line):
            if msg in line:
                c.acquire()
                c.notify_all()
                c.release()
                
                return True
        
        c.acquire()
        self._track_process(self._registry_proc, daemon_semaphore, wait=False)
        
        c.wait()
        
    def stop(self):
        self._registry_proc.terminate()
        self._registry_proc.wait()
    
    @contextlib.contextmanager
    def run(self):
        self.start()
        try:
            yield
        finally:
            self.stop()
            self.cleanup()

class RegistryStorage(object):
    
    def __init__(self, registry_path, api_version="v2"):
        super(RegistryStorage, self).__init__()
        
        self._api_version = api_version
        self._reg_path = registry_path
        
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def remove_repositories_without_tags(self):
        for r in os.listdir(self._get_repositories_path()):
            if not self.has_tags(r):
                self._logger.info("Removing data for repository %s", r)
                self.remove_repository(r)
    
    def _get_repositories_path(self):
        return "%s/docker/registry/%s/repositories" % (self._reg_path, self._api_version)
    
    def _get_repository_path(self, name):
        return "%s/%s" % (self._get_repositories_path(), name)
    
    def _get_tags_path(self, repository):
        return self._get_repository_path(repository) + "/_manifests/tags"
    
    def has_tags(self, repository):
        tags = os.listdir(self._get_tags_path(repository))
        return len(tags) > 0
    
    def remove_repository(self, name):
        shutil.rmtree(self._get_repository_path(name))
