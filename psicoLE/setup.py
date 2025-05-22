from setuptools import setup, find_packages

setup(
    name="psicoLE",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'flask-login',
        'flask-mail',
        'python-dotenv',
        'werkzeug',
        'email-validator',
    ],
    python_requires='>=3.6',
)
