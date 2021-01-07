"""Unit tests for reviewboard.admin.forms.EMailSettingsForm."""

from __future__ import unicode_literals

import kgb
from django.contrib import messages
from django.core import mail
from djblets.mail.message import EmailMessage
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.forms.email_settings import EMailSettingsForm, logger
from reviewboard.testing.testcase import TestCase


class EMailSettingsFormTestCase(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.admin.forms.EMailSettingsForm."""

    def test_save(self):
        """Testing EMailSettingsForm.save"""
        siteconfig = SiteConfiguration.objects.get_current()

        # Set defaults, so we know our changes are going to apply.
        siteconfig.set('mail_enable_autogenerated_header', False)
        siteconfig.set('mail_send_new_user_mail', False)
        siteconfig.set('mail_send_password_changed_mail', False)
        siteconfig.set('mail_send_review_close_mail', False)
        siteconfig.set('mail_send_review_mail', False)
        siteconfig.set('mail_use_tls', False)
        siteconfig.set('mail_default_from', 'noreply@example.com')
        siteconfig.set('mail_from_spoofing',
                       EmailMessage.FROM_SPOOFING_NEVER)
        siteconfig.set('mail_host', 'localhost')
        siteconfig.set('mail_host_password', '')
        siteconfig.set('mail_host_user', '')
        siteconfig.set('mail_port', 25)
        siteconfig.save()

        form = EMailSettingsForm(
            siteconfig,
            data={
                'mail_default_from': 'no-reply@mail.example.com',
                'mail_enable_autogenerated_header': True,
                'mail_from_spoofing': EmailMessage.FROM_SPOOFING_SMART,
                'mail_host': 'mail.example.com',
                'mail_host_password': 's3cr3t',
                'mail_host_user': 'mail-user',
                'mail_port': 123,
                'mail_send_new_user_mail': True,
                'mail_send_password_changed_mail': True,
                'mail_send_review_close_mail': True,
                'mail_send_review_mail': True,
                'mail_use_tls': True,
            })

        self.assertTrue(form.is_valid())
        form.save()

        # send_test_mail was not set.
        self.assertEqual(len(mail.outbox), 0)

        # Explicitly re-fetch this (without updating the cached copy) to
        # check the result.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertTrue(siteconfig.get('mail_enable_autogenerated_header'))
        self.assertTrue(siteconfig.get('mail_send_new_user_mail'))
        self.assertTrue(siteconfig.get('mail_send_password_changed_mail'))
        self.assertTrue(siteconfig.get('mail_send_review_close_mail'))
        self.assertTrue(siteconfig.get('mail_send_review_mail'))
        self.assertTrue(siteconfig.get('mail_use_tls'))
        self.assertEqual(siteconfig.get('mail_default_from'),
                         'no-reply@mail.example.com')
        self.assertEqual(siteconfig.get('mail_from_spoofing'),
                         EmailMessage.FROM_SPOOFING_SMART)
        self.assertEqual(siteconfig.get('mail_host'), 'mail.example.com')
        self.assertEqual(siteconfig.get('mail_host_password'), 's3cr3t')
        self.assertEqual(siteconfig.get('mail_host_user'), 'mail-user')
        self.assertEqual(siteconfig.get('mail_port'), 123)

    def test_save_with_send_test_mail_with_request(self):
        """Testing EMailSettingsForm.save with send_test_mail=True and with
        HTTP request
        """
        user = self.create_user(username='admin',
                                email='admin@corp.example.com')

        siteconfig = SiteConfiguration.objects.get_current()
        form = EMailSettingsForm(
            siteconfig,
            request=self.create_http_request(user=user),
            data={
                'mail_default_from': 'noreply@corp.example.com',
                'send_test_mail': True,
            })

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Review Board e-mail settings test')
        self.assertEqual(message.body,
                         "This is a test of the e-mail settings for the "
                         "Review Board server at http://example.com. If you "
                         "got this, you're all set!")
        self.assertEqual(message.to, ['admin@corp.example.com'])
        self.assertEqual(message.from_email, 'noreply@corp.example.com')

        # Explicitly re-fetch this (without updating the cached copy) to
        # check the result.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertNotIn('send_test_mail', siteconfig.settings)

    def test_save_with_send_test_mail_without_request(self):
        """Testing EMailSettingsForm.save with send_test_mail=True and without
        HTTP request
        """
        siteconfig = SiteConfiguration.objects.get_current()
        form = EMailSettingsForm(
            siteconfig,
            data={
                'mail_default_from': 'noreply@corp.example.com',
                'send_test_mail': True,
            })

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Review Board e-mail settings test')
        self.assertEqual(message.body,
                         "This is a test of the e-mail settings for the "
                         "Review Board server at http://example.com. If you "
                         "got this, you're all set!")
        self.assertEqual(message.to, ['admin@example.com'])
        self.assertEqual(message.from_email, 'noreply@corp.example.com')

        # Explicitly re-fetch this (without updating the cached copy) to
        # check the result.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)
        self.assertNotIn('send_test_mail', siteconfig.settings)

    def test_save_with_send_test_mail_with_request_and_error(self):
        """Testing EMailSettingsForm.save with send_test_mail=True with
        HTTP request and error sending e-mail
        """
        self.spy_on(logger.exception)
        self.spy_on(mail.send_mail,
                    op=kgb.SpyOpRaise(Exception('Kaboom!')))

        user = self.create_user(username='admin',
                                email='admin@corp.example.com')
        request = self.create_http_request(user=user)

        siteconfig = SiteConfiguration.objects.get_current()
        form = EMailSettingsForm(
            siteconfig,
            request=request,
            data={
                'mail_default_from': 'noreply@corp.example.com',
                'send_test_mail': True,
            })

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(len(mail.outbox), 0)
        self.assertSpyCalledWith(logger.exception,
                                 'Failed to send test e-mail to %s: %s',
                                 'admin@corp.example.com',
                                 'Kaboom!')

        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)

        msg = msgs[0]
        self.assertEqual(msg.level, messages.ERROR)
        self.assertEqual(msg.message,
                         'Failed to send the test e-mail: "Kaboom!". Check '
                         'the server logs for additional details.')

    def test_save_with_send_test_mail_without_request_and_error(self):
        """Testing EMailSettingsForm.save with send_test_mail=True without
        HTTP request and error sending e-mail
        """
        self.spy_on(logger.exception)
        self.spy_on(mail.send_mail,
                    op=kgb.SpyOpRaise(Exception('Kaboom!')))

        siteconfig = SiteConfiguration.objects.get_current()
        form = EMailSettingsForm(
            siteconfig,
            data={
                'mail_default_from': 'noreply@corp.example.com',
                'send_test_mail': True,
            })

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(len(mail.outbox), 0)
        self.assertSpyCalledWith(logger.exception,
                                 'Failed to send test e-mail to %s: %s',
                                 'admin@example.com',
                                 'Kaboom!')
