# app.py
import sys
from PyQt5.QtWidgets import QApplication, QDialog

from .splash import SplashScreen
from .login import LoginWindow
from .dashboards import LibrarianDashboard, MemberDashboard
from Roots.models import Librarian, Member

# Keep a global reference so the window doesn't get destroyed
main_window = None


def after_splash():
    global main_window

    print("Splash finished, opening login...")

    login = LoginWindow()
    result = login.exec_()

    print("Login dialog result:", result)
    print("Logged in user object:", login.logged_in_user)

    # If user cancelled or login failed, exit app
    if result != QDialog.Accepted or login.logged_in_user is None:
        print("Login cancelled or failed, exiting.")
        sys.exit(0)

    # Authenticated user (Librarian or Member)
    user = login.logged_in_user

    print("User type:", type(user))
    print("Selected role in login:", getattr(login, "role", None))

    # Choose dashboard based on selected role and user type
    if getattr(login, "role", None) == "librarian" and isinstance(user, Librarian):
        print("Opening LibrarianDashboard…")
        main_window = LibrarianDashboard(user)
    elif getattr(login, "role", None) == "member" and isinstance(user, Member):
        print("Opening MemberDashboard…")
        main_window = MemberDashboard(user)
    else:
        print("Role/type mismatch. Exiting.")
        sys.exit(0)

    main_window.show()
    print("Dashboard shown.")


def main():
    app = QApplication(sys.argv)

    splash = SplashScreen()
    splash.finished.connect(after_splash)
    splash.show()

    # Single event loop for the whole app
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
