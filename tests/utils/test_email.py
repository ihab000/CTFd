import six
from email.mime.text import MIMEText

if six.PY3:
    from email.message import EmailMessage

import requests
from freezegun import freeze_time
from mock import Mock, patch

from CTFd.utils import get_config, set_config
from CTFd.utils.email import (
    sendmail,
    verify_email_address,
    successful_registration_notification,
)
from tests.helpers import create_ctfd, destroy_ctfd


@patch("smtplib.SMTP")
def test_sendmail_with_smtp_from_config_file(mock_smtp):
    """Does sendmail work properly with simple SMTP mail servers using file configuration"""
    app = create_ctfd()
    with app.app_context():
        app.config["MAIL_SERVER"] = "localhost"
        app.config["MAIL_PORT"] = "25"
        app.config["MAIL_USEAUTH"] = "True"
        app.config["MAIL_USERNAME"] = "username"
        app.config["MAIL_PASSWORD"] = "password"

        ctf_name = get_config("ctf_name")
        from_addr = get_config("mailfrom_addr") or app.config.get("MAILFROM_ADDR")
        from_addr = "{} <{}>".format(ctf_name, from_addr)

        to_addr = "user@user.com"
        msg = "this is a test"

        sendmail(to_addr, msg)

        ctf_name = get_config("ctf_name")
        if six.PY2:
            email_msg = MIMEText(msg)
        else:
            email_msg = EmailMessage()
            email_msg.set_content(msg)

        email_msg["Subject"] = "Message from {0}".format(ctf_name)
        email_msg["From"] = from_addr
        email_msg["To"] = to_addr

        if six.PY2:
            mock_smtp.return_value.sendmail.assert_called_with(
                from_addr, [to_addr], email_msg.as_string()
            )
        else:
            mock_smtp.return_value.send_message.assert_called()
            assert str(mock_smtp.return_value.send_message.call_args[0][0]) == str(
                email_msg
            )
    destroy_ctfd(app)


@patch("smtplib.SMTP")
def test_sendmail_with_smtp_from_db_config(mock_smtp):
    """Does sendmail work properly with simple SMTP mail servers using database configuration"""
    app = create_ctfd()
    with app.app_context():
        set_config("mail_server", "localhost")
        set_config("mail_port", 25)
        set_config("mail_useauth", True)
        set_config("mail_username", "username")
        set_config("mail_password", "password")

        ctf_name = get_config("ctf_name")
        from_addr = get_config("mailfrom_addr") or app.config.get("MAILFROM_ADDR")
        from_addr = "{} <{}>".format(ctf_name, from_addr)

        to_addr = "user@user.com"
        msg = "this is a test"

        sendmail(to_addr, msg)

        ctf_name = get_config("ctf_name")
        if six.PY2:
            email_msg = MIMEText(msg)
        else:
            email_msg = EmailMessage()
            email_msg.set_content(msg)
        email_msg["Subject"] = "Message from {0}".format(ctf_name)
        email_msg["From"] = from_addr
        email_msg["To"] = to_addr

        if six.PY2:
            mock_smtp.return_value.sendmail.assert_called_with(
                from_addr, [to_addr], email_msg.as_string()
            )
        else:
            mock_smtp.return_value.send_message.assert_called()
            assert str(mock_smtp.return_value.send_message.call_args[0][0]) == str(
                email_msg
            )
    destroy_ctfd(app)


@patch.object(requests, "post")
def test_sendmail_with_mailgun_from_config_file(fake_post_request):
    """Does sendmail work properly with Mailgun using file configuration"""
    app = create_ctfd()
    with app.app_context():
        app.config["MAILGUN_API_KEY"] = "key-1234567890-file-config"
        app.config["MAILGUN_BASE_URL"] = "https://api.mailgun.net/v3/file.faked.com"

        to_addr = "user@user.com"
        msg = "this is a test"

        sendmail(to_addr, msg)

        fake_response = Mock()
        fake_post_request.return_value = fake_response
        fake_response.status_code = 200

        status, message = sendmail(to_addr, msg)

        args, kwargs = fake_post_request.call_args
        assert args[0] == "https://api.mailgun.net/v3/file.faked.com/messages"
        assert kwargs["auth"] == ("api", u"key-1234567890-file-config")
        assert kwargs["timeout"] == 1.0
        assert kwargs["data"] == {
            "to": ["user@user.com"],
            "text": "this is a test",
            "from": "CTFd <noreply@ctfd.io>",
            "subject": "Message from CTFd",
        }

        assert fake_response.status_code == 200
        assert status is True
        assert message == "Email sent"
    destroy_ctfd(app)


@patch.object(requests, "post")
def test_sendmail_with_mailgun_from_db_config(fake_post_request):
    """Does sendmail work properly with Mailgun using database configuration"""
    app = create_ctfd()
    with app.app_context():
        app.config["MAILGUN_API_KEY"] = "key-1234567890-file-config"
        app.config["MAILGUN_BASE_URL"] = "https://api.mailgun.net/v3/file.faked.com"

        # db values should take precedence over file values
        set_config("mailgun_api_key", "key-1234567890-db-config")
        set_config("mailgun_base_url", "https://api.mailgun.net/v3/db.faked.com")

        to_addr = "user@user.com"
        msg = "this is a test"

        sendmail(to_addr, msg)

        fake_response = Mock()
        fake_post_request.return_value = fake_response
        fake_response.status_code = 200

        status, message = sendmail(to_addr, msg)

        args, kwargs = fake_post_request.call_args
        assert args[0] == "https://api.mailgun.net/v3/db.faked.com/messages"
        assert kwargs["auth"] == ("api", u"key-1234567890-db-config")
        assert kwargs["timeout"] == 1.0
        assert kwargs["data"] == {
            "to": ["user@user.com"],
            "text": "this is a test",
            "from": "CTFd <noreply@ctfd.io>",
            "subject": "Message from CTFd",
        }

        assert fake_response.status_code == 200
        assert status is True
        assert message == "Email sent"
    destroy_ctfd(app)


@patch("smtplib.SMTP")
def test_verify_email(mock_smtp):
    """Does verify_email send emails"""
    app = create_ctfd()
    with app.app_context():
        set_config("mail_server", "localhost")
        set_config("mail_port", 25)
        set_config("mail_useauth", True)
        set_config("mail_username", "username")
        set_config("mail_password", "password")
        set_config("verify_emails", True)

        ctf_name = get_config("ctf_name")
        from_addr = get_config("mailfrom_addr") or app.config.get("MAILFROM_ADDR")
        from_addr = "{} <{}>".format(ctf_name, from_addr)

        to_addr = "user@user.com"

        with freeze_time("2012-01-14 03:21:34"):
            verify_email_address(to_addr)

        # This is currently not actually validated
        msg = (
            "Please click the following link to confirm"
            " your email address for CTFd:"
            " http://localhost/confirm/InVzZXJAdXNlci5jb20i.TxD0vg.28dY_Gzqb1TH9nrcE_H7W8YFM-U"
        )

        ctf_name = get_config("ctf_name")
        if six.PY2:
            email_msg = MIMEText(msg)
        else:
            email_msg = EmailMessage()
            email_msg.set_content(msg)
        email_msg["Subject"] = "Confirm your account for {ctf_name}".format(
            ctf_name=ctf_name
        )
        email_msg["From"] = from_addr
        email_msg["To"] = to_addr

        if six.PY2:
            mock_smtp.return_value.sendmail.assert_called_with(
                from_addr, [to_addr], email_msg.as_string()
            )
        else:
            mock_smtp.return_value.send_message.assert_called()
            assert str(mock_smtp.return_value.send_message.call_args[0][0]) == str(
                email_msg
            )
    destroy_ctfd(app)


@patch("smtplib.SMTP")
def test_successful_registration_email(mock_smtp):
    """Does successful_registration_notification send emails"""
    app = create_ctfd()
    with app.app_context():
        set_config("mail_server", "localhost")
        set_config("mail_port", 25)
        set_config("mail_useauth", True)
        set_config("mail_username", "username")
        set_config("mail_password", "password")
        set_config("verify_emails", True)

        ctf_name = get_config("ctf_name")
        from_addr = get_config("mailfrom_addr") or app.config.get("MAILFROM_ADDR")
        from_addr = "{} <{}>".format(ctf_name, from_addr)

        to_addr = "user@user.com"

        successful_registration_notification(to_addr)

        msg = "You've successfully registered for CTFd!"

        if six.PY2:
            email_msg = MIMEText(msg)
        else:
            email_msg = EmailMessage()
            email_msg.set_content(msg)
        email_msg["Subject"] = "Successfully registered for {ctf_name}".format(
            ctf_name=ctf_name
        )
        email_msg["From"] = from_addr
        email_msg["To"] = to_addr

        if six.PY2:
            mock_smtp.return_value.sendmail.assert_called_with(
                from_addr, [to_addr], email_msg.as_string()
            )
        else:
            mock_smtp.return_value.send_message.assert_called()
            assert str(mock_smtp.return_value.send_message.call_args[0][0]) == str(
                email_msg
            )
    destroy_ctfd(app)
