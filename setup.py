import os
import re
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()

with open("%s/src/glorpen/docker_registry_cleaner/__init__.py" % (here,), "rt") as f:
    data = f.read()
    version = re.search(r'^__version__\s*=\s*"([^"]+)', data, re.MULTILINE).group(1)
    description = re.search(r'^__description__\s*=\s*"([^"]+)', data, re.MULTILINE).group(1)

requires = [
    'requests~=2.21',
    'glorpen-config~=2.1',
    'glorpen-di~=1.5',
    'natsort~=6.0',
    'semver~=2.8',
    'py-expression-eval~=0.3',
    'pyyaml~=5.1',
]

suggested_require = []
dev_require = []
tests_require = ['unittest']

setup(
    name='docker-registry-cleaner',
    version = version,
    description=description,
    long_description=README + '\n\n' + CHANGES,
    author='Arkadiusz Dzięgiel',
    author_email='arkadiusz.dziegiel@glorpen.pl',
    url="https://github.com/glorpen/docker-registry-cleaner",
    keywords='docker registry v2 cleaner untagger',
    packages=["glorpen.docker_registry_cleaner"],
    extras_require={
        'testing': tests_require + suggested_require,
        'development': dev_require + tests_require + suggested_require,
        'suggested': suggested_require
    },
    install_requires=requires,
    python_requires='>=3.5,<4.0',
    namespace_packages=["glorpen"],
    package_dir={'':'src'},
    zip_safe=True,
    include_package_data=True,
    test_suite="glorpen.docker_registry_cleaner.tests",
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
    ],
)
