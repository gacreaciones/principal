from flask_login import LoginManager, AnonymousUserMixin

class AnonymousUser(AnonymousUserMixin):
    def __init__(self):
        self.username = 'Invitado'

login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser