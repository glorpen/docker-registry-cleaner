'''
Created on 4 kwi 2019

.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
'''
import os
import shutil
import logging
import subprocess
import yaml
import pkg_resources
import contextlib
import threading
import glob
import pathlib

class NativeRegistry(object):
    """Allows executing registry commands using real registry binary.
    
    Supports garbage-collect command and running local registry binary with delete support enabled.
    """
    
    _config_path = "/tmp/registry-config.yaml"
    """Path used to create runtime config for docker registry binary."""
    
    _registry_proc = None
    
    def __init__(self, registry_data, registry_bin, registry_address):
        """
        :param registry_data: Path to registry datadir.
        :type registry_data: str
        :param registry_bin: Path to registry binary.
        :type registry_bin: str
        :param registry_address: Address that registry should listen on.
        :type registry_address: str
        """
        super(NativeRegistry, self).__init__()
        
        self.registry_data = registry_data
        self.registry_address = registry_address
        self.registry_bin = registry_bin
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.registry_logger = logging.getLogger("%s:registry" % self.__class__.__name__)
    
    def _save_config(self):
        if not os.path.exists(self._config_path):
            with pkg_resources.resource_stream(__package__, 'resources/registry.yaml') as f:
                d = yaml.safe_load(f)
                
                d["storage"]["filesystem"]["rootdirectory"] = self.registry_data
                d["http"]["addr"] = self.registry_address
                
                with open(self._config_path, "wt") as f:
                    yaml.dump(d, f)
        
        return self._config_path
    
    def cleanup(self):
        """Removes runtime configs and temporary files."""
        if os.path.exists(self._config_path):
            os.unlink(self._config_path)
    
    def garbage_collect(self):
        """Starts registry binary in garbage-collect mode and waits for completion.
        
        Will throw an Exception when failed.
        
        :raises: Exception
        """
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
        """Starts registry daemon and blocks until it is initialized."""
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
        """Stop running processes, does not clean temporary data."""
        self._registry_proc.terminate()
        self._registry_proc.wait()
    
    @contextlib.contextmanager
    def run(self):
        """Starts and stops registry process."""
        self.start()
        try:
            yield
        finally:
            self.stop()
            self.cleanup()

class RegistryStorage(object):
    """Manages raw registry files."""
    
    def __init__(self, registry_path, api_version="v2"):
        """
        :param registry_path: Path to registry datadir.
        :type registry_path: str
        """
        super(RegistryStorage, self).__init__()
        
        self._api_version = api_version
        self._reg_path = registry_path
        
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def remove_repositories_without_tags(self):
        """Checks repositories in registry data dir and removes ones without tags.""" 
        repos_path = self._get_repositories_path()
        for p in glob.glob('%s/**/_manifests/tags' % repos_path, recursive=True):
            r = str(pathlib.Path(p).relative_to(repos_path).parent.parent)
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
        """Checks if tags directory for given repository is not empty.
        
        :param repository: Repository name.
        :type repository: str
        """
        tags = os.listdir(self._get_tags_path(repository))
        return len(tags) > 0
    
    def remove_repository(self, name):
        """
        Deletes all files for given repository.
        
        .. warning::
        
            there is no rollback, your data will be gone
        
        :param name: Repository name.
        :type name: str
        
        """
        shutil.rmtree(self._get_repository_path(name))
