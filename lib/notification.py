import logging
import smtplib
from collections import defaultdict
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from typing import Dict, Any

from lib.config import Config




class Notification:
    mails = {}
    smtp = None

    @classmethod
    def add(cls, recipients, text, highlight=""):
        """
            Register new project related notification as a mail.
        :param project:
        :param recipients: Mail or list of mails.
        :param status:
        :param owner:
        """
        if type(recipients) is str:
            recipients = [recipients]

        for r in recipients:
            if not r in cls.mails:
                cls.mails[r] = Notification(r)
            o = cls.mails[r]
            o.text.append(text)
            if highlight:
                o.subject.append(highlight)

    def __init__(self, email_to):
        self.email_to = email_to
        self.subject = []
        self.text = []

    def build_mail(self, send=True):
        subject = "shifts"
        if self.subject:
            subject += " (" + ",".join(self.subject) + ")"

        text = "<br>\r\n".join(self.text) + "<br>\r\n<br>\r\n" + f"Wanna plan <a href='{Config.config.get('general','application_url')}'>a shift</a>?"

        email_from = Config.config.get("general", "email_from")
        msg = MIMEText(text, "html", "utf-8")
        msg["From"] = email_from
        msg["Subject"] = subject
        msg["To"] = self.email_to
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        if send:
            self.smtp.sendmail(email_from, self.email_to , msg.as_string().encode('ascii'))
            pass
        if Config.verbose: # not send
            msg.set_payload("")
            print("\n----------------\n\n", msg, text)


    @classmethod
    def send(cls, send=True):
        try:
            smtp = Config.config.get("general", "smtp_server")
            with smtplib.SMTP(smtp) as cls.smtp:
                for m in cls.mails.values():
                    m.build_mail(send)
        except ConnectionRefusedError:
            logging.error(f"Can't connect to the SMTP server: {smtp}")
