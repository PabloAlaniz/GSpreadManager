import os
from setuptools import setup, find_packages

# Obtener la ruta absoluta al directorio donde se encuentra setup.py
HERE = os.path.abspath(os.path.dirname(__file__))

# Abrir el README.md desde esa ruta
with open(os.path.join(HERE, 'README.md'), encoding='utf-8') as fh:
    long_description = fh.read()
setup(
    name='GSpreadManager',
    version='0.1.5',
    author='PabloAlaniz',
    author_email='pablo@culturainteractiva.com',
    description='Un módulo de Python para gestionar y automatizar tareas en Google Sheets.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/PabloAlaniz/GSpreadManager',
    packages=find_packages(),
    install_requires=[
        'gspread>=3.0',
        'oauth2client>=4.0',
        'pandas>=1.2.4',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
