from setuptools import setup

setup(
    name='adbrv',
    version='1.1.0',
    description='ADB reverse port forwarding and HTTP proxy configuration for Android devices.',
    author='kx4n9',
    author_email='dthkhang@gmail.com',
    url='https://github.com/dthkhang/adbrv',
    py_modules=['adbrv'],
    entry_points={
        'console_scripts': [
            'adbrv=adbrv:main',
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