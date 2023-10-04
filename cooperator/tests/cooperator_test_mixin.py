# SPDX-FileCopyrightText: 2019 Coop IT Easy SC
# SPDX-FileContributor: Robin Keunen <robin@coopiteasy.be>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta


class CooperatorTestMixin:
    @classmethod
    def set_up_cooperator_test_data(cls):
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
        cls.company.coop_email_contact = "coop_email@example.org"
        cls.demo_partner = cls.env.ref("base.partner_demo")
        company_share_category = cls.env.ref(
            "cooperator.product_category_company_share"
        )
        cls.share_x = cls.env["product.product"].create(
            {
                "name": "Share X - Founder",
                "short_name": "Share X",
                "default_code": "share_x",
                "categ_id": company_share_category.id,
                "is_share": True,
                "by_individual": True,
                "by_company": False,
                "list_price": 50,
            }
        )
        cls.share_y = cls.env["product.product"].create(
            {
                "name": "Share Y - Worker",
                "short_name": "Share Y",
                "default_code": "share_y",
                "categ_id": company_share_category.id,
                "is_share": True,
                "default_share_product": True,
                "by_individual": True,
                "by_company": True,
                "list_price": 25,
            }
        )
        cls.subscription_request_1 = cls.env["subscription.request"].create(
            {
                "firstname": "John",
                "lastname": "Doe",
                "email": "john@test.com",
                "address": "Cooperation Street",
                "zip_code": "1111",
                "city": "Brussels",
                "lang": "en_US",
                "country_id": cls.env.ref("base.be").id,
                "date": datetime.now() - timedelta(days=12),
                "source": "manual",
                "ordered_parts": 3,
                "share_product_id": cls.share_y.id,
                "data_policy_approved": True,
                "internal_rules_approved": True,
                "financial_risk_approved": True,
                "generic_rules_approved": True,
                "gender": "male",
                "iban": "09898765454",
                "birthdate": date(1990, 9, 21),
                "skip_iban_control": True,
            }
        )

    @classmethod
    def create_company(cls, name):
        company = cls.env["res.company"].create(
            {
                "name": name,
            }
        )
        # apply the same account chart template as the main company
        cls.company.chart_template_id.try_loading(company)
        return company

    def pay_invoice(self, invoice, payment_date=None):
        ctx = {"active_model": "account.move", "active_ids": [invoice.id]}
        register_payments_vals = {"payment_type": "inbound"}
        if payment_date is not None:
            register_payments_vals["payment_date"] = payment_date
        register_payment = (
            self.env["account.payment.register"]
            .with_context(**ctx)
            .create(register_payments_vals)
        )
        register_payment.with_company(invoice.company_id).action_create_payments()

    def create_payment_account_move(self, invoice, date, amount=None):
        if amount is None:
            amount = invoice.line_ids[0].credit
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "bank"),
                ("company_id", "=", invoice.company_id.id),
            ],
            limit=1,
        )
        am = self.env["account.move"].create(
            {
                "journal_id": journal.id,
                "date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": invoice.name,
                            "account_id": journal.default_account_id.id,
                            "debit": amount,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": invoice.payment_reference,
                            "account_id": invoice.company_id.property_cooperator_account.id,
                            "credit": amount,
                        },
                    ),
                ],
                "company_id": invoice.company_id.id,
            }
        )
        am.action_post()
        (invoice.line_ids[-1] + am.line_ids[-1]).reconcile()
        return am

    def get_dummy_subscription_requests_vals(self):
        return {
            "share_product_id": self.share_y.id,
            "ordered_parts": 2,
            "firstname": "first name",
            "lastname": "last name",
            "email": "email@example.net",
            "phone": "dummy phone",
            "address": "dummy street",
            "zip_code": "dummy zip",
            "city": "dummy city",
            "country_id": self.ref("base.be"),
            "lang": "en_US",
            "gender": "other",
            "birthdate": "1980-01-01",
            "iban": "BE60096123456870",
            "source": "manual",
        }

    def get_dummy_company_subscription_requests_vals(self):
        vals = self.get_dummy_subscription_requests_vals()
        vals.update(
            {
                "is_company": True,
                "company_name": "dummy company",
                "company_email": "companyemail@example.net",
                "company_register_number": "dummy company register number",
                "contact_person_function": "dummy contact person function",
            }
        )
        return vals

    def create_dummy_subscription_request(self):
        return self.env["subscription.request"].create(
            self.get_dummy_subscription_requests_vals()
        )

    def create_dummy_company_subscription_request(self):
        return self.env["subscription.request"].create(
            self.get_dummy_company_subscription_requests_vals()
        )

    def create_dummy_subscription_from_partner(self, partner):
        vals = self.get_dummy_subscription_requests_vals()
        vals["partner_id"] = partner.id
        return self.env["subscription.request"].create(vals)

    def create_dummy_subscription_from_company_partner(self, partner):
        vals = self.get_dummy_company_subscription_requests_vals()
        vals["partner_id"] = partner.id
        return self.env["subscription.request"].create(vals)

    def validate_subscription_request_and_pay(self, subscription_request):
        subscription_request.validate_subscription_request()
        self.pay_invoice(subscription_request.capital_release_request)

    def create_dummy_cooperator(self):
        subscription_request = self.create_dummy_subscription_request()
        self.validate_subscription_request_and_pay(subscription_request)
        return subscription_request.partner_id

    def create_dummy_company_cooperator(self):
        subscription_request = self.create_dummy_company_subscription_request()
        self.validate_subscription_request_and_pay(subscription_request)
        return subscription_request.partner_id
