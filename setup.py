from setuptools import setup, find_packages

setup(
    name='jco',
    version='0.1.0',

    author='Yuriy Homyakov',
    author_email='yuriy.homyakov@gmail.com',

    license='MIT',

    description='Jibrel Network ICO support site',

    packages=find_packages(),
    include_package_data=True,

    install_requires=['requests==2.18.4',
                      'requests[socks]==2.18.4',
                      'Flask==0.12.2',
                      'Flask-Cors==3.0.3',
                      'Flask-Mail==0.9.1',
                      'Flask-Migrate==2.1.1',
                      'Flask-RESTful==0.3.6',
                      'Flask-Script==2.0.6',
                      'Flask-jsontools==0.1.1.post0',
                      'Jinja2==2.9.6',
                      'validate-email==1.3',
                      'celery==4.1.0',
                      'uWSGI==2.0.15',
                      'pycoin==0.80',
                      'mnemonic==0.13',
                      'CommonConfig',
                      'AppDB',
                      'CommonUtils']
)
