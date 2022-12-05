from setuptools import setup

setup(
    name="rbclib",
    version="0.3.0",
    packages=["rbclib"],
    install_requires=[
        "chainpy @ git+https://github.com/bifrost-platform/bifrost-python-lib.git"
    ]
)
