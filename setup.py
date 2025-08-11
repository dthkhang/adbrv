from setuptools import setup

setup(
    name='adbrv',
    version='1.4.0',
        version='1.4.1',
    description='ADB reverse port forwarding, HTTP proxy configuration, and APK resign (uber-apk-signer) for Android devices.',
    author='kx4n9',
    author_email='dthkhang@gmail.com',
    url='https://github.com/dthkhang/adbrv',
    packages=['adbrv_module'],
    py_modules=['adbrv'],
    package_data={
        'adbrv_module': ['tools/uber-apk-signer-1.3.0.jar'],
    },
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