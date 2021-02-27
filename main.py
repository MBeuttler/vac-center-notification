import requests
import json
import smtplib
import ssl
from datetime import datetime
from json2html import *
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import argparse


def send_mail(content, username, password, sender_email, receiver_email, smtp_server, smtp_port=465, start_tls=False):
    message = MIMEMultipart("alternative")
    message["Subject"] = "Freie Impftermine"
    message["From"] = username
    message["To"] = receiver_email

    # Create the plain-text and HTML version of your message
    email_text = json.dumps(content, indent=4, sort_keys=True, ensure_ascii=False)
    html = json2html.convert(json=content)

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(email_text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    if start_tls:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()  # Can be omitted
        server.starttls(context=context)  # Secure the connection
        server.ehlo()  # Can be omitted
        server.login(sender_email, password)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )
    else:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receiver_email, message.as_string()
            )


def get_all_vac_centers():
    url = "https://www.impfterminservice.de/assets/static/impfzentren.json"
    headers = {
        'cache-control': "no-cache",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
    }

    r = requests.get(url=url, timeout=5, headers=headers)

    return r.json()


def list_vac_centers():
    vac_centers = get_all_vac_centers()
    json.dumps(vac_centers, indent=4, sort_keys=True, ensure_ascii=False)


def search_appointments(vac_center_names=[]):

    appointment_path = 'rest/suche/termincheck?plz='
    appointment_key = 'termineVorhanden'

    headers = {
        'cache-control': "no-cache",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
        }

    free_appointments = []

    vac_centers = get_all_vac_centers()

    for state in vac_centers.keys():
        for vac_center in vac_centers[state]:

            # only look up vac centers of interest
            if len(vac_center_names) > 0  and vac_center['Zentrumsname'] not in vac_center_names:
                continue

            try:
                # skip vac centers that don't provide the needed keys (Hessen and NRW do have their own website)
                if 'URL' not in vac_center or len(vac_center['URL']) == 0:
                    print('Missing URL: Skipping {}'.format(vac_center))
                    continue
                # skip vac centers that don't provide the needed keys (Hessen and NRW do have their own website)
                if 'PLZ' not in vac_center or len(vac_center['PLZ']) == 0:
                    print('Missing PLZ: Skipping {}'.format(vac_center))
                    continue

                appointment_url = '{0}{1}{2}'.format(vac_center['URL'], appointment_path, vac_center['PLZ'])
                r = requests.get(url=appointment_url, timeout=5, headers=headers)
                appointment_response = r.json()

                if appointment_key not in appointment_response or appointment_response[appointment_key]:
                    print('{}-{}'.format(vac_center['Bundesland'], vac_center['Zentrumsname']))
                    free_appointments.append(vac_center)
            except:
                print("Unexpected error:", sys.exc_info()[0])

    if len(free_appointments) <= 0:
        print('No free appointments found')

    return free_appointments


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Check `impfterminservice` for free appointments')
    parser.add_argument('--vac-centers', dest='vac_centers', type=str,
                        help='comma seperated list of `Zentrumsname`. Use --list to get a list of all possible values.')
    parser.add_argument('--list', dest='show_list', action='store_true',
                        help='List all possible values for --vac-centers')
    parser.add_argument('--email-from', dest='email_from', type=str, required=True,
                        help='Sending e-mail address')
    parser.add_argument('--email-to', dest='email_to', type=str, required=True,
                        help='Receiving e-mail address')
    parser.add_argument('--smtp-user', dest='smtp_user', type=str, required=True,
                        help='login name for smtp server')
    parser.add_argument('--smtp-password', dest='smtp_password', type=str, required=True,
                        help='login password for smtp server')
    parser.add_argument('--smtp-server', dest='smtp_server', type=str, default='smtp.gmail.com',
                        help='smtp server address')
    parser.add_argument('--smtp-port', dest='smtp_port', type=int, default=465,
                        help='smtp server port')
    parser.add_argument('--start-tls', dest='start_tls', type=bool, default=False,
                        help='If start tls should be used. Default is ssl')
    parser.add_argument('--always-send', dest='always_send', action='store_true',
                        help='By default emails are only send if free appointments are found')

    args = parser.parse_args()

    if args.show_list:
        list_vac_centers()

    vac_centers_of_interest = [vac_center.strip() for vac_center in args.vac_centers.split(',')]

    # parse website
    appointments = search_appointments(vac_centers_of_interest)

    if len(appointments) > 0 or args.always_send:
        send_mail({
            'Datum': datetime.now().isoformat(),
            'Überwachte Impfzentren': vac_centers_of_interest,
            'Impfzentren mit freien Terminen': appointments
        },
            username=args.smtp_user,
            password=args.smtp_password,
            sender_email=args.email_from,
            receiver_email=args.email_to,
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            start_tls=args.start_tls
        )