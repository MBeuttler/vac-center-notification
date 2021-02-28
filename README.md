# vac-center-notification
Python crawler that parses german vac centers (https://www.impfterminservice.de/) for free appointments.
Can be automated with cron or some other scheduler to regularly check the website and send notification via email.
The python cmd script can be found under `python_cmd/find_vac_appointments.py` and an scheduler example based on 
homeassistant `python_homeassistant/vac_ha_app.py` 

Not working for `Hessen` and `NRW` as they have a custom website for appointments.

# Python cmd

## Install
[Get/Install Python 3.7](https://www.python.org/downloads/release/python-370/)
```bash
pip install -r requirements.txt
```

## How to use
```bash
usage: find_vac_appointments.py [-h] [--zip-codes VAC_CENTERS] [--list]
                                --email-from EMAIL_FROM --email-to EMAIL_TO
                                --smtp-user SMTP_USER --smtp-password
                                SMTP_PASSWORD [--smtp-server SMTP_SERVER]
                                [--smtp-port SMTP_PORT]
                                [--start-tls START_TLS] [--always-send]

Check `impfterminservice` for free appointments

optional arguments:
  -h, --help            show this help message and exit
  --zip-codes VAC_CENTERS
                        comma separated list of vaccination center zip-codes
                        (or `ALL`). Use --list to get a list of all possible
                        values.
  --list                List all vac centers and zip-codes
  --email-from EMAIL_FROM
                        Sending e-mail address
  --email-to EMAIL_TO   Comma separated list of receiving e-mail addresses
  --smtp-user SMTP_USER
                        login name for smtp server
  --smtp-password SMTP_PASSWORD
                        login password for smtp server
  --smtp-server SMTP_SERVER
                        smtp server address
  --smtp-port SMTP_PORT
                        smtp server port
  --start-tls START_TLS
                        If start tls should be used. Default is ssl
  --always-send         By default emails are only send if free appointments
                        are found
```
# Homeassistant App

## Install
[Home Assistant](https://www.home-assistant.io/)
[AppDaemon](https://appdaemon.readthedocs.io)

## Install python libs via AppDaemon config
```bash
system_packages: []
python_packages:
  - json2html
  - requests
init_commands: []
```

## How to use
copy vac_ha_app.py to `/config/appdaemon/apps/`

edit `/config/appdaemon/apps/apps.yaml`
```bash
vac_ha_app:
    module: vac_ha_app
    class: VacCrawler
    smtp_user: your_username
    smtp_password: your_password
    email_from: your_email
    email_to: your_email
    smtp_server: your_smtp_server
    smtp_port: 465
    start_tls: False
    vac_centers: ALL | comma separated list of vaccination center zip-codes
    always_send: False
```
