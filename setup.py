from setuptools import setup
from relayer.__init__ import __version__

setup(
    name="rbclib",
    version=__version__,
    packages=["rbclib"],
    install_requires=[
        "chainpy @ git+https://github.com/bifrost-platform/bifrost-python-lib.git@0.4.1"
    ]
)
