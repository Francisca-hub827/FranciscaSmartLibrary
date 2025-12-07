This branch (feature/login) is used for login-related changes for the SmartLibrary
# Francisca SmartLibrary

SmartLibrary is a desktop library application built for Limkokwing University – Sierra Leone.  
It manages **books, authors, members, book clubs and loans**, with a Python OOP backend and a PyQt5 GUI.  
The app connects to a PostgreSQL database (tables, triggers, SQL queries are kept separately in pgAdmin as required by the assignment).

---

## Tech stack

- **Language:** Python 3.x  
- **GUI:** PyQt5 (dashboards, login, book & member windows)  
- **Database:** PostgreSQL (tables, triggers, views, functions – *not stored in this repo*)  
- **Version control:** Git + GitHub  
- **CI / DevOps:** GitHub Actions (Python tests & linting)

---

## Project structure

```text
FranciscaSmartLibrary/
  gui/          # PyQt5 windows (login, dashboards, books, members, clubs, splash)
  Roots/        # Backend logic: DAOs, models, database access layer
  .idea/        # IDE configuration (PyCharm/IntelliJ)

#How to run the app (local machine)

-Create a virtual environment and activate it.

-Install dependencies:

pip install -r requirements.txt

Make sure your PostgreSQL database is running and the connection settings in Roots/daos.py (or your config file) are correct.

Run the application (example if gui/app.py is the entry point):

python -m gui.app

(Small change after fixing GitHub Actions workflow filename.)

