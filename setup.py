from setuptools import setup, find_packages

setup(
    name='nexuzy-data-collector',
    version='1.0.0',
    description='AI-Powered India Travel Data Collection & Verification System',
    author='David - Nexuzy Tech',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'requests>=2.32',
        'beautifulsoup4>=4.12',
        'lxml>=5.0',
        'trafilatura>=1.12',
        'newspaper3k>=0.2.8',
        'pandas>=2.0',
        'numpy>=1.26',
        'openpyxl>=3.1',
        'pyarrow>=18.0',
        'fuzzywuzzy>=0.18',
        'python-levenshtein>=0.25',
        'tqdm>=4.67',
        'loguru>=0.7',
        'pyyaml>=6.0',
        'python-dotenv>=1.0',
        'schedule>=1.2',
        'httpx>=0.28',
        'geopy>=2.4',
        'jsonlines>=4.0',
        'markdown>=3.7',
        'Pillow>=11.0',
        'sqlite-utils>=3.37',
    ],
    entry_points={
        'console_scripts': [
            'nexuzy-collector=main:main',
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
    ]
)
