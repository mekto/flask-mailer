"""
Flask-Mailer
-------------

A Flask extension for sending email messages.
"""
from setuptools import setup


setup(
    name='Flask-Mailer',
    version='0.1',
    url='https://github.com/mekto/flask-mailer',
    license='BSD',
    author='Tomasz Krzyszczyk',
    author_email='tomasz.krzyszczyk@gmail.com',
    description='A Flask extension for sending email messages.',
    long_description=__doc__,
    py_modules=['flask_mailer'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask', 'pyinotify'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)