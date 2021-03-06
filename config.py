import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET KEY') or 'you-will-never-guess'

    #SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')       #DJG - Not needed now using Flask-Migrate with Flask-Script
    #SQLALCHEMY_COMMIT_ON_TEARDOWN = True       #DJG - Should be set to true but causes session errors http://stackoverflow.com/questions/23301968/invalid-transaction-persisting-across-requests

    UPLOADS_DEFAULT_DEST = os.path.join(basedir, 'uploads')  # DJG - This is a guess copied from above, what does it do?
    UPLOADS_DEFAULT_URL = "/"

    RECAPTCHA_PUBLIC_KEY = '6LeYIbsSAAAAACRPIllxA7wvXjIE411PfdB2gt2J'
    RECAPTCHA_PRIVATE_KEY = '6LeYIbsSAAAAAJezaIq3Ft_hSTo0YtyeFG-JgRtu'

    COURSEME_MAIL_SUBJECT_PREFIX = '[CourseMe]'
    COURSEME_MAIL_SENDER='CourseMe Info <info.courseme@gmail.com>'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL=False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'courseme-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'courseme-test.sqlite')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'courseme.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}