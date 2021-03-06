import requests
import json
import smtplib
import ssl
from datetime import datetime
from json2html import *
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import hassapi as hass
import datetime


class VacCrawler(hass.Hass):

    def send_mail(self, content, username, password, sender_email, receiver_email, smtp_server, smtp_port=465,
                  start_tls=False):
        self.log('sending mails')

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

    def get_all_vac_centers(self):
        url = "https://www.impfterminservice.de/assets/static/impfzentren.json"
        headers = {
            'cache-control': "no-cache",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
        }

        r = requests.get(url=url, timeout=5, headers=headers)

        return r.json()

    def get_vaccination_list(self, base_url):
        path = "/assets/static/its/vaccination-list.json"
        headers = {
            'cache-control': "no-cache",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
        }

        r = requests.get(url=base_url + path, timeout=5, headers=headers)

        return r.json()

    def search_appointments(self, vac_center_zip_codes=None, rq_qualifications=None):
        if vac_center_zip_codes is None:
            vac_center_zip_codes = []

        appointment_path = 'rest/suche/termincheck?'
        appointment_key = 'termineVorhanden'

        headers = {
            'cache-control': "no-cache",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
        }

        free_appointments = []

        vac_centers = self.get_all_vac_centers()

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

                    vaccination_list = self.get_vaccination_list(vac_center['URL'])

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
                            print('{}-{}'.format(vac_center['Bundesland'], vac_center['Zentrumsname'],
                                                 qualification_name))
                            vac_center_has_appointments = True

                    if vac_center_has_appointments:
                        free_appointments.append(vac_center)

                except:
                    print("Unexpected error:", sys.exc_info()[0])

        if len(free_appointments) <= 0:
            print('No free appointments found')

        return free_appointments

    # initialize() function which will be called at startup and reload
    def initialize(self):
        self.log("VAC HA App Running")
        time = datetime.datetime.now()
        self.run_every(self.run_callback, time, interval=self.args['interval'], random_start=-60*5, random_end=60*5)

    def run_callback(self, kwargs):
        # Call to Home Assistant to turn the porch light on
        self.log("run callback: {}".format(self.args['vac_centers']))

        if self.args['vac_centers'] is None or len(self.args['vac_centers']) == 0:
            vac_centers_of_interest = []
        else:
            vac_centers_of_interest = [vac_center.strip() for vac_center in self.args['vac_centers'].split(',')]

        # parse website
        appointments = self.search_appointments(vac_centers_of_interest, self.args['qualifications'])

        if len(appointments) > 0 or self.args['always_send']:
            self.send_mail({
                'Datum': datetime.datetime.now().isoformat(),
                'Überwachte Impfzentren': vac_centers_of_interest,
                'Impfzentren mit freien Terminen': appointments
            },
                username=self.args['smtp_user'],
                password=self.args['smtp_password'],
                sender_email=self.args['email_from'],
                receiver_email=self.args['email_to'],
                smtp_server=self.args['smtp_server'],
                smtp_port=self.args['smtp_port'],
                start_tls=self.args['start_tls']
            )