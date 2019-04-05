'''
Created on 4 kwi 2019

@author: glorpen
'''
import tempfile
import yaml
from glorpen.docker_registry_cleaner.console import Cli
import os
import contextlib
from glorpen.docker_registry_cleaner import api

def generate_config(repositories):
    f = tempfile.NamedTemporaryFile(mode="w+t", delete=False)
    yaml.dump({
        "repositories": repositories
    }, f)
    f.close()
    
    return f.name

@contextlib.contextmanager
def _app(repositories):
    config = generate_config(repositories)
    app = Cli().create_app(
        config,
        os.environ.get("REGISTRY_DATA", "/var/lib/registry"),
        os.environ.get("REGISTRY_BIN", "registry")
    )
    try:
        yield app
    finally:
        os.unlink(config)
        app.close()

@contextlib.contextmanager
def _registry(url="http://127.0.0.1:5000"):
    registry = api.DockerRegistry(url, {})
    yield registry
    registry.close()