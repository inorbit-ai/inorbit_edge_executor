from setuptools import setup, find_packages

setup(
    name="inorbit_edge_executor",
    version="2.0.0",
    description="InOrbit Edge Missions Executor",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Mariano Cereda, Hernan Badenes",
    author_email="mariano.cereda@inorbit.ai, herchu@inorbit.ai",
    packages=find_packages(include=["inorbit_edge_executor"]),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.21",
        "requests",
        "python-dotenv",
        "inorbit-edge>=1.16.2",
        "pytz>=2022.7",
        "pyyaml",
        "uuid",
        "async-timeout==4.0.3",
        "autopep8==2.0.0",
        "certifi",
        "click==8.1.3",
        "httpx==0.24.1",
        "idna==3.4",
        "itsdangerous==2.1.2",
        "MarkupSafe==2.1.1",
        "pycodestyle==2.10.0",
        "pydantic",
        "pytest",
        "python-dotenv==0.21.0",
        "PyYAML==5.3.1",
        "six==1.16.0",
        "tomli==2.0.1",
        "typing-extensions==4.7.1",
        "urllib3==1.26.13",
        "pytest==7.4.0",
        "pytest-httpx==0.22.0",
        "pytest-asyncio==0.21.1",
        "aiosql==9.0",
        "aiosqlite==0.19.0",
        "pydantic-settings",
        "dpath",
        "pydantic-yaml",
    ],
    extras_require={
        "dev": [
            "pytest", "black", "tox", "bump2version~=1.0", "black~=24.3", "coverage~=7.4", "flake8~=7.0",
            "flake8-pyproject~=1.2", "pip~=24.0", "pytest~=8.1", "pytest-mock~=3.14", "requests-mock~=1.12",
            "setuptools~=68.2", "tox~=4.14", "twine~=5.0", "wheel~=0.43"
        ],
        "docs": ["sphinx", "mkdocs"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)