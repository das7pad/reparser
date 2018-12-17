#!/usr/bin/env python

from setuptools import setup

install_requires = []

setup(
    name="ReParser",
    version="1.4.3",
    description="Simple regex-based lexer/parser for inline markup",
    author="Michal Krenek (Mikos)",
    author_email="m.krenek@gmail.com",
    maintainer=", ".join((
        "Jakob Ackermann <das7pad@outlook.com>",
    )),
    maintainer_email="das7pad@outlook.com",
    url="https://github.com/xmikos/reparser",
    license="MIT",
    packages=["reparser"],
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup"
    ]
)
