from setuptools import setup

setup(
    name='adb-rvproxy',
    version='1.0.0',
    description='ADB reverse port forwarding and HTTP proxy configuration for Android devices.',
    author='kx4n9 akd Khang Duong',
    author_email='dthkhang@gmail.com',
    url='https://github.com/dthkhang',
    py_modules=['adb_rvproxy'],
    entry_points={
        'console_scripts': [
            'adbrv=adb_rvproxy:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
    ],
    python_requires='>=3.6',
)
