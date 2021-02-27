# vac-center-notification
Python crawler that parses german vac centers (https://www.impfterminservice.de/) for free appointments.
Can be automated with cron or some other scheduler to regularly check the website and send notification via email.

Not working for `Hessen` and `NRW` as they have a custom website for appointments.

# HOW TO INSTALL
```bash
[Get/Install Python 3.7](https://www.python.org/downloads/release/python-370/)
pip install -r requirements.txt
```

# HOW TO USE
```bash
usage: main.py [-h] [--vac-centers VAC_CENTERS] [--list] --email-from
               EMAIL_FROM --email-to EMAIL_TO --smtp-user SMTP_USER
               --smtp-password SMTP_PASSWORD [--smtp-server SMTP_SERVER]
               [--smtp-port SMTP_PORT] [--start-tls START_TLS] [--always-send]

Check `impfterminservice` for free appointments

optional arguments:
  -h, --help            show this help message and exit
  --vac-centers VAC_CENTERS
                        comma seperated list of `Zentrumsname`. Use --list to
                        get a list of all possible values.
  --list                List all possible values for --vac-centers
  --email-from EMAIL_FROM
                        Sending e-mail address
  --email-to EMAIL_TO   Receiving e-mail address
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

Process finished with exit code 0
```
