#!/usr/bin/env python3

import string
import requests
import smtplib
import os

from pathlib import Path
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

load_dotenv()


class Constants:
    """Constants for the program"""
    HTTPERROR = 'Http Error:'
    HTTPERRORCONNECT = "Error Connecting:"
    HTTPTIMEOUT = "Timeout Error:"
    HTTPOOPS = "OOps: Something Else:"
    EMAILERROR = "Email Error:"
    TWILIOERROR = "Error Sending SMS:"


class KS():
    def __init__(self):
        '''Constructor'''
        self.project = os.getenv('PROJECT')
        self.user = os.getenv('USER')
        self.url = os.getenv('URL')

    def ks_url(self) -> string:
        '''Return the Kickstarter url'''
        return self.url + '/' \
            + self.user + '/' + self.project + '/'

    def kickstarter(self) -> dict:
        '''Return the Kickstarter data'''
        try:
            r = requests.get(
                self.ks_url() + '/stats.json?v=1',
                timeout=int(os.getenv('TIMEOUT_RETRIES'))
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            print(Constants.HTTPERROR, errh)
        except requests.exceptions.ConnectionError as errc:
            print(Constants.HTTPERRORCONNECT, errc)
        except requests.exceptions.Timeout as errt:
            print(Constants.HTTPTIMEOUT, errt)
        except requests.exceptions.RequestException as err:
            print(Constants.HTTPOOPS, err)

        return r.json()


class File():
    """File class for the program"""
    @staticmethod
    def Write(count: int, file) -> None:
        '''Write the count to the file'''
        open(file, 'w').write(str(count))

    @staticmethod
    def Read() -> int:
        '''Return the last backer count'''
        file = File.File()

        if not os.path.exists(file):
            File.Write(0, file)
            return

        with open(file) as f:
            count = f.readline().rstrip()

        return count

    @staticmethod
    def File() -> string:
        '''Return the data file name'''
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file = dir_path + '/' + os.getenv('DATA_FILE')
        file = Path(file).resolve()

        return file


class Notify():
    """Notify class for the program"""
    @staticmethod
    def Email(data: dict) -> None:
        '''Send an email.'''
        message = MIMEMultipart("alternative")
        message["Subject"] = f"New backer alert! \
            {data['current_count']} backers!"
        message["From"] = os.getenv('GMAIL_USER')
        message["To"] = os.getenv('EMAIL_RECIPIENTS')
        body = f"\
            Congrats! Your new backer count: \
            {data['current_count']}!<br />\
            Previous count: {data['previous_count']}<br /><br />\
            Pledge amount: <strong> \
            {str(round(float(data['pledge']), 2))}</strong><br />"

        message.attach(MIMEText(body, "html"))

        try:
            server = smtplib.SMTP_SSL(
                os.getenv('SMTP_SERVER'),
                os.getenv('SMTP_PORT')
            )
            server.ehlo()
            server.login(
                os.getenv('GMAIL_USER'),
                os.getenv('GMAIL_PASS')
            )
            server.sendmail(
                os.getenv('GMAIL_USER'),
                os.getenv('EMAIL_RECIPIENTS'),
                message.as_string()
            )
            server.close()
        except Exception as e:
            print(f'{Constants.EMAILERROR} {e}')

    @staticmethod
    def Twilio(data: dict) -> None:
        '''Send an SMS'''
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )

        try:
            message = client.messages.create(
                body=f"New backer alert! \
                    {data['current_count']} backers! \
                    Pledge amount: \
                    {str(round(float(data['pledge']), 2))}",

                from_=os.getenv('TWILIO_FROM_NUMBER'),
                to=os.getenv('TWILIO_TO_NUMBER')
            )
        except TwilioRestException as e:
            print(f'{Constants.TWILIOERROR} {message.id} : {e}')


def main() -> None:
    backers = KS()

    print("----Starting KS-Notify")
    data = backers.kickstarter()

    previous_count = File.Read()

    print("Previous Count: " + str(previous_count))

    if previous_count == "" or previous_count == None:
        previous_count = 0

    previous_count = int(previous_count)
    current_count = data['project']['backers_count'] or 0

    print("Current Count: " + str(current_count))

    if current_count > previous_count:
        File.Write(current_count, File.File())
        pledge = data['project']['pledged'] or 0

        if os.getenv('SEND_EMAIL') == 'true':
            Notify.Email({'current_count': current_count,
                          'previous_count': previous_count,
                          'pledge': pledge
                          })

        if os.getenv('SEND_SMS') == 'true':
            Notify.Twilio({'current_count': current_count,
                           'previous_count': previous_count,
                           'pledge': pledge
                           })

        print('New backer! New pledge amount: $' + str(pledge))
    else:
        print('No new backers, sorry!')

    print("End KS-Notify----")


if __name__ == '__main__':
    main()
