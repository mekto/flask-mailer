import os
import time
import random
import shutil
import smtplib
import sys
from threading import Timer

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate
from email import message_from_file

from flask.globals import current_app
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_CREATE


__all__ = ['Email']


class Email(object):

    def __init__(self, subject, recipients=None, sender=None, body_plain=None, body_html=None):

        self.subject = subject
        self.recipients = recipients
        self.sender = sender or current_app.config['MAILER_DEFAULT_SENDER']
        self.body_plain = body_plain
        self.body_html = body_html

    def to_message(self):
        msg = MIMEMultipart('mixed')
        msg['Subject'] = self.subject
        msg['From'] = self.sender
        msg['To'] = ', '.join(self.recipients)
        msg['Data'] = formatdate(localtime=True)
        msg.preamble = 'This is a multi-part message in MIME format.'

        if self.body_plain and self.body_html:
            # Encapsulate the plain and HTML versions of the message body in an 'alternative' part, so message agents can decide which they want to display.
            alternative = MIMEMultipart('alternative')
            alternative.attach(MIMEText(self.body_plain.encode('utf-8'), 'plain', 'utf-8'))
            alternative.attach(MIMEText(self.body_html.encode('utf-8'), 'html', 'utf-8'))
            msg.attach(alternative)
        else:
            if self.body_plain:
                msg.attach(MIMEText(self.body_plain.encode('utf-8'), 'plain', 'utf-8'))
            if self.body_html:
                msg.attach(MIMEText(self.body_html.encode('utf-8'), 'html', 'utf-8'))

        return msg

    def as_string(self):
        return self.to_message().as_string()

    def send(self):
        filename = '{0}.{1}.eml'.format(int(time.time()), mkssid(10))
        with open(os.path.join(get_path('outbox'), filename), 'w') as f:
            f.write(self.as_string().encode('utf-8'))


def get_path(subdir=None, app=None):
    path = os.path.abspath((app or current_app).config['MAILER_PATH'])
    if subdir:
        path = os.path.join(path, subdir)
    if not os.path.exists(path):
        os.makedirs(path, mode=0777)
    return path


def extract_email_from_string(s):
    if s.rfind('<') > -1:
        return s[s.rfind('<') + 1:s.rfind('>')].strip()
    return s.strip()


def mkssid(length=5):
  x = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  rv = ''
  for i in xrange(length):
    rv += x[int(random.random()*62)]
  return rv


class Console(object):

    @classmethod
    def write(cls, string, *args, **kwargs):
        sys.stdout.write(string.format(*args, **kwargs))
        sys.stdout.flush()

    @classmethod
    def writeline(cls, string, *args, **kwargs):
        cls.write(string + '\n', *args, **kwargs)


class MailerEventHandler(ProcessEvent):

    def __init__(self, callback):
        self.timer = None
        self.callback = callback

    def process_IN_CREATE(self, event):
        if not self.timer:
            timer = Timer(3, self.execute)
            timer.start()

    def execute(self):
        self.timer = None
        self.callback()


class Mailer(object):

    def __init__(self, app):
        self.app = app
        self.outbox_path = get_path('outbox', app=self.app)
        self.sent_path = get_path('sent', app=self.app)
        self.failed_path = get_path('failed', app=self.app)

        self.smtp_sender = self.app.config.get('MAILER_SMTP_SENDER')
        self.smtp_user = self.app.config.get('MAILER_SMTP_USER')
        self.smtp_pass = self.app.config.get('MAILER_SMTP_PASSWORD')

    def send_from_path(self, path):
        emails = []
        not_sent_emails = []

        for filename in os.listdir(path):
            if filename.endswith('.eml'):
                emails.append(os.path.join(path, filename))

        if not emails:
            return

        Console.write('Sending {0} email(s) from [{1}]... ', len(emails), os.path.basename(path))
        try:
            server = smtplib.SMTP(self.app.config['MAILER_SMTP_SERVER'])
            if self.smtp_user:
                server.login(self.smpt_user, self.smtp_pass)

            for filename in emails:
                try:
                    with open(filename, 'r') as f:
                        email = message_from_file(f)
                    sender = self.smtp_sender or extract_email_from_string(email['From'])
                    msg_to = [extract_email_from_string(address) for address in email['To'].split(',')]

                    server.sendmail(sender, msg_to, email.as_string())
                    shutil.move(filename, os.path.join(self.sent_path, os.path.basename(filename)))
                    Console.write('SENT ')
                except Exception, e:
                    Console.write('SENDING ERROR ')
                    not_sent_emails.append(filename)
                    print e

            Console.writeline('')
            server.quit()
        except Exception, e:
            Console.writeline('ERROR')
            print e

        if not_sent_emails:
            for filename in not_sent_emails:
                shutil.move(filename, os.path.join(self.failed_path, os.path.basename(filename)))

    def send_from_outbox(self):
        self.send_from_path(self.outbox_path)

    def run(self):
        self.send_from_outbox()

        wm = WatchManager()
        wm.add_watch(self.outbox_path.__str__(), IN_CREATE)

        notifier = Notifier(wm, MailerEventHandler(self.send_from_outbox))
        while True:
            try:
                notifier.process_events()
                if notifier.check_events():
                    notifier.read_events()
            except KeyboardInterrupt:
                notifier.stop()
                break

try:
    from flask.ext.script import Command

    class MailerCommand(Command):

        description = 'Runs the mailer.'

        def handle(self, app):
            # we don't need to run the server in request context
            # so just run it directly
            mailer = Mailer(app)
            mailer.run()

    __all__.append('MailerCommand')
except:
    pass
