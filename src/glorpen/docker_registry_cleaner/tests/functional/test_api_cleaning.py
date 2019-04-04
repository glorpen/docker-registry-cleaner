'''
Created on 4 kwi 2019

@author: glorpen
'''
import unittest
from glorpen.docker_registry_cleaner.console import Cli
from glorpen.docker_registry_cleaner.tests.functional import fixtures
import os
from glorpen.docker_registry_cleaner import api
import logging
import contextlib

class TestApi(unittest.TestCase):
    
    def _get_repositories_config(self, max_items=0):
        return {
          "all": {
              "paths": ["*"],
              "cleaners": {
                  "other": {
                      "type": "max",
                      "max_items": max_items
                  }
              }
          }
        }
    
    @contextlib.contextmanager
    def _app(self, repositories):
        config = fixtures.generate_config(repositories)
        app = Cli().create_app(config, "/var/lib/registry")
        try:
            yield app
        finally:
            os.unlink(config)
            app.close()
    
    @contextlib.contextmanager
    def _registry(self, url="http://127.0.0.1:5000"):
        registry = api.DockerRegistry(url, {})
        yield registry
        registry.close()
    
    def test_cleaning_whole_repos(self):
        with self._app(self._get_repositories_config(0)) as app:
            self.assertNotIn("simple-cleaning", app.list_repos(), "No image before uploading")
            with app._native.run():
                with self._registry() as r:
                    r.upload_fake_image('simple-cleaning', 'latest', b'1231231232')
            self.assertDictContainsSubset({"simple-cleaning": ("latest",)}, app.list_repos(), "Image after uploading")
            app.clean()
            self.assertNotIn("simple-cleaning", app.list_repos(), "No image after cleaning")
    
    def test_cleaning_some_images(self):
        with self._app(self._get_repositories_config(1)) as app:
            with app._native.run():
                with self._registry() as r:
                    r.upload_fake_image('some-cleaning', '2', b'3333333332')
                    r.upload_fake_image('some-cleaning', '1', b'1231231232')
            app.clean()
            self.assertDictContainsSubset({"some-cleaning": ("2",)}, app.list_repos(), "Second image was not removed")
    
    def test_cross_tagging(self):
        with self._app(self._get_repositories_config(1)) as app:
            with app._native.run():
                with self._registry() as r:
                    r.upload_fake_image('first-cross-cleaning', '1', b'3333333332')
                    r.upload_fake_image('second-cross-cleaning', '1', b'3333333331')
                    r.upload_fake_image('first-cross-cleaning', '2', b'3333333331')
                    r.upload_fake_image('second-cross-cleaning', '2', b'3333333332')
            app.clean()
            self.assertDictContainsSubset({"first-cross-cleaning": ("2",), "second-cross-cleaning": ("2",)}, app.list_repos(), "Newer images are not removed")
