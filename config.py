import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
#    MAIL_SERVER = 'smtp.googlemail.com'
#    MAIL_PORT = 587
#    MAIL_USE_TLS = True
#    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
#    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
#    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
#    FLASKY_MAIL_SENDER = 'Flasky Admin <flasky@example.com>'
#    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')

    #SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')


    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'courseme-dev.db')

    UPLOADS_DEFAULT_DEST = os.path.join(basedir, 'uploads')      #DJG - This is a guess copied from above, what does it do?
    UPLOADS_DEFAULT_URL = "/"

    RECAPTCHA_PUBLIC_KEY = '6LeYIbsSAAAAACRPIllxA7wvXjIE411PfdB2gt2J'
    RECAPTCHA_PRIVATE_KEY = '6LeYIbsSAAAAAJezaIq3Ft_hSTo0YtyeFG-JgRtu'




# class TestingConfig(Config):
#     TESTING = True
#     SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
#         'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
#
#
# class ProductionConfig(Config):
#     SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
#         'sqlite:///' + os.path.join(basedir, 'data.sqlite')


config = {
    'development': DevelopmentConfig,
#    'testing': TestingConfig,
#    'production': ProductionConfig,

    'default': DevelopmentConfig
}