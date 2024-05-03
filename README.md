# Planetarium API Service
###### The Planetarium Booking System lets visitors easily book tickets online for upcoming ShowSessions at the local Planetarium.

## Installing

```shell
git clone https://github.com/eugenevsn/planetarium_api_service/
cd planetarium_api_service

python -m venv .venv
source .venv/Scripts/activate

pip install -r requirements.txt
python manage.py migrate

python manage.py runserver
```


## Running with Docker
###### Docker should be installed

```shell
docker-compose build

docker-compose up
```


## Getting Access:

### Create user:
> api/user/register/

### Get access token: 
> api/user/token/


## Documentation:

> api/doc/swagger/

> api/doc/redoc/
