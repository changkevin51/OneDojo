# OneDojo

A very exceptional dojo management app.

1. clone the repo
  ```bash
https://github.com/changkevin51/Dojo-App.git
```
2. run these in the terminal

(Note: the database (sqlite) is NOT pushed into this repo so you actually need to run all this and register the users)

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

to go to admin panel type /admin after the website link and then login with the super user username and password

dont push anything unless you're absolutely sure it works


## Team

Kevin Chang, Ray Xu, Michael Wang

