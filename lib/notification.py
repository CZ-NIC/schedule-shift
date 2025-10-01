import logging
import smtplib
from collections import defaultdict
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from typing import Dict, Any

from envelope import Envelope

from lib.config import Config, config


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

        text = "<br>\r\n".join(self.text) + "<br>\r\n<br>\r\n" + \
            f"Wanna plan <a href='{config.env.application_url}'>a shift</a>?"

        e = (Envelope().from_(config.env.email_from)
                       .to(self.email_to)
                       .subject(subject)
                       .message(text)
                       .smtp(self.smtp))

        if send:
            e.send()
            pass
        if Config.verbose:  # not send
            print("\n----------------\n\n", e.preview())

    @classmethod
    def send(cls, send=True):
        try:
            smtp = config.env.smtp_server
            with smtplib.SMTP(smtp) as cls.smtp:
                for m in cls.mails.values():
                    m.build_mail(send)
        except ConnectionRefusedError:
            logging.error(f"Can't connect to the SMTP server: {smtp}")
