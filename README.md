## Setting up your python virtual environment
1. Navigate to your project root directory `capstone-project-3900h18bthebinarybrotherhood`.Then run the command:
```
python3 -m venv env
```
Now you've created a new python virtual environment. 
- The second argument `env` creates a folder called `env`.
- `env` is the where we will install your virtual python installation. 
- This was done using `venv` which is a virtual environment manager. 
2. Now you must activate your python virtual environment. Do this by running the command:
```
source env/bin/activate
```
3. Confirm you're in the right virtual environment using1s
```
which python
```
this should give something like 
```
.../capstone-project-3900h18bthebinarybrotherhood/env/bin/python
```
4. Nice, now lets install the packages using pip that you actually need for the project. Do this using:
```
pip install -r requirements.txt
```
Also get the requirements for devs so we can all use the same linting tools.
```
pip install -r requirements-dev.txt
```
5. Lastly, set up environment variables in an .env file
```
SERIALIZER_SECRET_KEY="REDACTED"
EVENTSTAR_EMAIL="REDACTED"
EVENTSTAR_EMAIL_PASSWORD="REDACTED"
```

## Interacting with the database
### PGADMIN
1. Install pgadmin to interact easily with the database. https://www.pgadmin.org/download/
2. Once you have pgadmin installed you need to add our database to pgadmin. To do this click on `Add new server`
In the general section enter:
- Name: PGDATABASE

In the connection section enter: 
- Hostname/address: PGHOST
- Port: PGDATABASE: PGPORT
- Maintenance database: PGDATABASE
- Username: PGUSER
- Password: PGPASSWORD 
4. Now you should be able to see the database, add tables, edit remove or query.

### Python
1. To interact with the DB python you need to make sure `database.py` is able to create a postgres scheme URL to connect to the database. Since it gets some parts of this using environment variables you need to setup your environment variables using the following command:
```
export PGDATABASE="REDACTED"
export PGHOST="REDACTED"
export PGPORT="REDACTED"
export PGUSER="REDACTED"
export PGPASSWORD="REDACTED"
```
**NOTE:**
You should be able to get these credentials seperately.

## Running the backend
1. Enter your python virtual environment
2. If making new environment remember to install requirements.
3. Enter environment variables.
4. `uvicorn app.main:app --reload` from project backend directory.

## To restore the postgres DB run this command:
```
SELECT pg_cancel_backend(629554) FROM pg_stat_activity WHERE state = 'active' and pid <> pg_backend_pid();
```
Replace `629554` with the blocking PID.

## Setup the formatting to AU

```
sudo locale-gen en_AU.UTF-8
```