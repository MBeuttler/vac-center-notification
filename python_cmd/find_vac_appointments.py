from operator import le

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

    receivers = receiver_email.split(',')

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
            sender_email, receivers, message.as_string()
        )
    else:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receivers, message.as_string()
            )


def get_all_vac_centers():
    url = "https://www.impfterminservice.de/assets/static/impfzentren.json"
    headers = {
        'cache-control': "no-cache",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
    }

    r = requests.get(url=url, timeout=5, headers=headers)

    return r.json()


def get_vaccination_list(base_url):
    path = "/assets/static/its/vaccination-list.json"
    headers = {
        'cache-control': "no-cache",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
    }

    r = requests.get(url=base_url + path, timeout=5, headers=headers)

    return r.json()


def list_vac_centers():
    vac_centers = get_all_vac_centers()
    print(json.dumps(vac_centers, indent=4, sort_keys=True, ensure_ascii=False))


def search_appointments(vac_center_zip_codes=None, rq_qualifications=None):
    if vac_center_zip_codes is None:
        vac_center_zip_codes = []

    appointment_path = 'rest/suche/termincheck?'
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
            if len(vac_center_zip_codes) > 0 and vac_center['PLZ'] not in vac_center_zip_codes:
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

                vaccination_list = get_vaccination_list(vac_center['URL'])

                if rq_qualifications is None or len(rq_qualifications) <= 0:
                    qualifications = ','.join(vaccination['qualification'] for vaccination in vaccination_list)
                else:
                    qualifications = rq_qualifications

                vac_center_has_appointments = False
                for qa in qualifications.split(','):
                    qualification_name = [vaccination['name'] for vaccination in vaccination_list if
                                          vaccination['qualification'] == qa]

                    appointment_url = '{0}{1}plz={2}&leistungsmerkmale={3}'.format(
                        vac_center['URL'], appointment_path, vac_center['PLZ'], qa)

                    r = requests.get(url=appointment_url, timeout=5, headers=headers)
                    appointment_response = r.json()

                    vac_center[qa] = {
                        'Impfstoff': qualification_name,
                        'Termine Vorhanden': appointment_response['termineVorhanden']
                    }

                    if appointment_key in appointment_response and appointment_response[appointment_key]:
                        print('{}-{}'.format(vac_center['Bundesland'], vac_center['Zentrumsname'], qualification_name))
                        vac_center_has_appointments = True

                if vac_center_has_appointments:
                    free_appointments.append(vac_center)

            except:
                print("Unexpected error:", sys.exc_info()[0])

    if len(free_appointments) <= 0:
        print('No free appointments found')

    return free_appointments


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Check `impfterminservice` for free appointments')
    parser.add_argument('--zip-codes', dest='vac_centers', type=str,
                        help='comma separated list of vaccination center zip-codes. Use --list to get a list of all possible values.')
    parser.add_argument('--qualifications', dest='requested_qualifications', type=str,
                        help='comma separated list of needed qualifications. Use --list-qualifications to get a list of all possible values.')
    parser.add_argument('--list', dest='show_list', action='store_true',
                        help='List all vac centers and zip-codes')
    parser.add_argument('--list-qualifications', dest='show_qa_list', action='store_true',
                        help='List all qualifications')
    parser.add_argument('--email-from', dest='email_from', type=str, required=True,
                        help='Sending e-mail address')
    parser.add_argument('--email-to', dest='email_to', type=str, required=True,
                        help='Comma separated list of receiving e-mail addresses')
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

        sys.exit()

    if args.show_qa_list:
        vac_centers = get_all_vac_centers()

        qualification_list = {}

        for state in vac_centers.keys():
            for vac_center in vac_centers[state]:
                if 'URL' in vac_center and len(vac_center['URL']) and 'PLZ' in vac_center and len(
                        vac_center['PLZ']) > 0:
                    vaccinations = get_vaccination_list(vac_center['URL'])
                    for vac in vaccinations:
                        qualification_list[vac['qualification']] = vac

        print(json.dumps(qualification_list, indent=4, sort_keys=True, ensure_ascii=False))

        sys.exit()

    if args.vac_centers is None or len(args.vac_centers) == 0:
        vac_centers_of_interest = []
    else:
        vac_centers_of_interest = [vac_center.strip() for vac_center in args.vac_centers.split(',')]

    # parse website
    appointments = search_appointments(vac_centers_of_interest, args.requested_qualifications)

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
