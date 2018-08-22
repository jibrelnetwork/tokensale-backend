from datetime import datetime
from typing import List, Optional

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import synonym

from jco.appdb.db import db


class CurrencyType:
    token = 'TOKEN'
    btc = 'BTC'
    eth = 'ETH'
    usd = 'USD'
    eur = 'EUR'
    chf = 'CHF'


class AffiliateNetwork:
    clicksure = 'clicksure'
    runcpa = 'runcpa'
    actionpay = 'actionpay'
    adpump = 'adpump'


class AffiliateStatus:
    success = 200


class AffiliateEvent:
    registration = 'registration'
    transaction = 'transaction'


class TransactionStatus:
    not_confirmed = 'not_confirmed'
    confirmed = 'confirmed'
    pending = 'pending'
    fail = 'fail'
    success = 'success'


class NotificationType:
    # Registration
    account_created         = 'account_created'
    account_email_confirmed = 'account_email_confirmed'

    # KYC
    kyc_data_received       = 'kyc_data_received'
    kyc_account_rejected    = 'account_rejected'

    # Account
    password_change_request = 'password_change_request'
    password_changed        = 'password_changed'
    withdraw_address_change_request = 'withdraw_address_change_request'
    withdraw_address_changed        = 'withdraw_address_changed'

    # Transactions
    transaction_received    = 'transaction_received'
    transaction_received_sold_out = 'transaction_received_sold_out'
    transaction_received_sold_out_admin = 'transaction_received_sold_out_admin'
    withdrawal_request      = 'withdrawal_request'
    withdrawal_succeeded    = 'withdrawal_succeeded'
    withdrawal_processed    = 'withdrawal_processed'

    presale_account_created    = 'presale_account_created'


# account_01_01 = "Password change request"
# account_01_02 = "Your password was updated"
# account_02_01 = "ETH Address change request"
# account_02_02 = "Your ETH Address was updated"

# kyc_01 = "Completing your TOKEN purchase"
# kyc_02 = "Unable to verify your identity"

# registration_01 = "Verify your email address"
# registration_02 = "Accessing your Token Sale Dashboard"

# transactions_01 = "Your purchase of ~{{transaction_token_amount}} TOKEN was successful!"
# transactions_02_01 = "TOKEN withdrawal request"
# transactions_02_02 = "TOKEN withdrawal underway"
# transactions_03 = "Your TOKEN was transferred successfully!"
# transactions_04 = "Token sale closed"


NOTIFICATION_KEYS = {
    NotificationType.account_created: 'registration_01',
    NotificationType.account_email_confirmed: 'registration_02',

    NotificationType.kyc_data_received: 'kyc_01',
    NotificationType.kyc_account_rejected: 'kyc_02',

    NotificationType.password_change_request: 'account_01_01',
    NotificationType.password_changed: 'account_01_02',

    NotificationType.withdraw_address_change_request: 'account_02_01',
    NotificationType.withdraw_address_changed: 'account_02_02',

    NotificationType.transaction_received: 'transactions_01',
    NotificationType.transaction_received_sold_out: 'transactions_04',
    NotificationType.transaction_received_sold_out_admin: 'transactions_04_admin',
    NotificationType.withdrawal_request: 'transactions_02_01',
    NotificationType.withdrawal_succeeded: 'transactions_03',
    NotificationType.withdrawal_processed: 'transactions_02_02',
    NotificationType.presale_account_created: 'presale_01',
}

NOTIFICATION_SUBJECTS = {
    'account_01_01': 'Password change request',
    'account_01_02': 'Your password was updated',
    'account_02_01': 'ETH Address change request',
    'account_02_02': 'Your ETH Address was updated',
    'kyc_01': 'Completing your TOKEN purchase',
    'kyc_02': 'Unable to verify your identity',
    'registration_01': 'Verify your email address',
    'registration_02': 'Accessing your Token Sale Dashboard',
    'transactions_01': 'Your purchase of {transaction_token_amount} TOKEN was successful!',
    'transactions_02_01': 'TOKEN withdrawal request',
    'transactions_02_02': 'TOKEN withdrawal underway',
    'transactions_03': 'Your TOKEN was transferred successfully!',
    'transactions_04': 'Token sale closed',
    'transactions_04_admin': 'Token sale closed',
    'presale_01': 'Your Jibrel Network Tokens have arrived!',
}


class User(db.Model):
    """
    Django auth user
    """

    __tablename__ = 'auth_user'

    id = db.Column(db.Integer, primary_key=True)
    pk = synonym('id')
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)

    # Relationships
    addresses = db.relationship('Address',
                                back_populates="user",
                                cascade="all, delete-orphan",
                                passive_deletes=True)  # type: Address
    withdraws = db.relationship('Withdraw',
                                back_populates="user",
                                cascade="all, delete-orphan",
                                passive_deletes=True)  # type: Withdraw
    account = db.relationship('Account',
                               back_populates="user",
                               uselist=False,
                               passive_deletes=True)  # type: Account
    notifications = db.relationship('Notification',
                                    back_populates="user",
                                    cascade="all, delete-orphan",
                                    passive_deletes=True)  # type: Notification
    affiliates = db.relationship('Affiliate',
                                 back_populates="user",
                                 cascade="all, delete-orphan",
                                 passive_deletes=True)  # type: Affiliate
    presales = db.relationship('PresaleToken',
                                 back_populates="user",
                                 cascade="all, delete-orphan",
                                 passive_deletes=True)  # type: PresaleToken
    custom_token_prices = db.relationship('UserTokenPrice',
                                 back_populates="user",
                                 cascade="all, delete-orphan",
                                 passive_deletes=True)  # type: UserTokenPrice

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('username', self.username),
                         ('email', self.email))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)

    def as_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username
        }


class Account(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False, default='')
    last_name = db.Column(db.String(120), nullable=False, default='')
    fullname = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(120), nullable=False)
    street = db.Column(db.String(120), nullable=False, default='')
    town = db.Column(db.String(120), nullable=False, default='')
    postcode = db.Column(db.String(120), nullable=False, default='')
    citizenship = db.Column(db.String(120), nullable=False)
    residency = db.Column(db.String(120), nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    terms_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    notified = db.Column(db.Boolean, nullable=False, default=False)
    is_identity_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_identity_verification_declined = db.Column(db.Boolean, nullable=False, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=True)
    withdraw_address = db.Column(db.String(255), nullable=False, default='')

    document_url = db.Column(db.String(200), nullable=False, default='')
    document_type = db.Column(db.String(20), nullable=False, default='')
    is_document_skipped = db.Column(db.Boolean, nullable=False, default=False)

    verification_attempts = db.Column(db.Integer, nullable=False, default=0)
    is_presale_account = db.Column(db.Boolean, nullable=False, default=False)
    is_sale_allocation = db.Column(db.Boolean, nullable=False, default=True)
    tracking = db.Column(JSONB, nullable=False, default=lambda: {})

    # Relationships
    user = db.relationship(User, back_populates="account")  # type: User

    # Tracking keys
    tracking_key_affiliate_clicksureclickid = 'clicksureclickid'
    tracking_key_affiliate_track_id = 'track_id'
    tracking_key_affiliate_actionpay = 'actionpay'
    tracking_key_affiliate_adpump = 'adpump'

    # Methods

    def get_affiliate_clicksureclickid(self) -> Optional[str]:
        if self.tracking_key_affiliate_clicksureclickid not in self.tracking:
            return None
        return self.tracking[self.tracking_key_affiliate_clicksureclickid]

    def get_affiliate_track_id(self) -> Optional[str]:
        if self.tracking_key_affiliate_track_id not in self.tracking:
            return None
        return self.tracking[self.tracking_key_affiliate_track_id]

    def get_affiliate_actionpay(self) -> Optional[str]:
        if self.tracking_key_affiliate_actionpay not in self.tracking:
            return None
        return self.tracking[self.tracking_key_affiliate_actionpay]

    def get_affiliate_adpump(self) -> Optional[str]:
        if self.tracking_key_affiliate_adpump not in self.tracking:
            return None
        return self.tracking[self.tracking_key_affiliate_adpump]

    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('fullname', self.fullname),
                         ('email', self.email),
                         ('country', self.country),
                         ('citizenship', self.citizenship),
                         ('created', self.created),
                         ('notified', self.notified))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)

    def as_dict(self):
        return {
            'id': self.id,
            'fullname': self.fullname,
            'country': self.country,
            'citizenship': self.citizenship,
            'created': self.created,
            'notified': self.notified,
        }


class Address(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    is_usable = db.Column(db.Boolean, nullable=False, default=True)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=False)

    # Relationships
    transactions = db.relationship('Transaction',
                                   back_populates="address",
                                   cascade="all, delete-orphan",
                                   passive_deletes=True,
                                   order_by='Transaction.id')  # type: List[Transaction]

    user = db.relationship(User, back_populates="addresses")  # type: User

    # Meta keys
    meta_key_force_scanning = 'force_scanning'

    # Methods
    def get_force_scanning(self) -> Optional[bool]:
        if self.meta_key_force_scanning not in self.meta:
            return None
        return self.meta[self.meta_key_force_scanning]

    def set_force_scanning(self, value: bool):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_force_scanning] = value
        flag_modified(self, "meta")

    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('address', self.address),
                         ('type', self.type),
                         ('is_usable', self.is_usable),
                         ('meta', self.meta))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)

    def as_dict(self):
        return {
            'id': self.id,
            'address': self.address,
            'type': self.type,
            'is_usable': self.is_usable,
        }


class Transaction(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(120), unique=True, nullable=False)
    value = db.Column(db.Float, nullable=False)
    mined = db.Column(db.DateTime, nullable=False)
    block_height = db.Column(db.Integer, nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False, default=TransactionStatus.pending)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Relationships
    address = db.relationship(Address, back_populates="transactions")  # type: Address
    token_purchase = db.relationship('TOKEN',
                                   back_populates="transaction",
                                   cascade="all, delete-orphan",
                                   passive_deletes=True,
                                   uselist=False)  # type: TOKEN

    # Meta keys
    meta_key_notified = 'notified'
    meta_key_failed_notifications = 'failed_notifications'
    meta_key_mailgun_message_id = 'mailgun_message_id'
    meta_key_mailgun_delivered = 'mailgun_delivered'
    meta_key_skip_token_calculation = 'skip_token_calculation'

    # Methods
    def as_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'value': self.value,
            'mined': self.mined,
            'block_height': self.block_height,
            'address_id': self.address_id,
            'address': self.address.as_dict(),
            'mailgun_message_id': self.get_mailgun_message_id(),
            'mailgun_delivered': self.get_mailgun_delivered(),
            'currency': self.address.type,
        }

    def get_notified(self) -> Optional[bool]:
        if self.meta_key_notified not in self.meta:
            return None
        return self.meta[self.meta_key_notified]

    def set_notified(self, value: bool):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_notified] = value
        flag_modified(self, "meta")

    def get_failed_notifications(self) -> Optional[int]:
        if self.meta_key_failed_notifications not in self.meta:
            return None
        return self.meta[self.meta_key_failed_notifications]

    def set_failed_notifications(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_failed_notifications] = value
        flag_modified(self, "meta")

    def get_mailgun_message_id(self) -> Optional[str]:
        if self.meta_key_mailgun_message_id not in self.meta:
            return None
        return self.meta[self.meta_key_mailgun_message_id]

    def set_mailgun_message_id(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_mailgun_message_id] = value
        flag_modified(self, "meta")

    def get_mailgun_delivered(self) -> Optional[str]:
        if self.meta_key_mailgun_delivered not in self.meta:
            return None
        return self.meta[self.meta_key_mailgun_delivered]

    def set_mailgun_delivered(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_mailgun_delivered] = value
        flag_modified(self, "meta")

    def get_skip_token_calculation(self) -> Optional[bool]:
        if self.meta_key_skip_token_calculation not in self.meta:
            return None
        return self.meta[self.meta_key_skip_token_calculation]

    def set_skip_token_calculation(self, value: bool):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_skip_token_calculation] = value
        flag_modified(self, "meta")

    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('transaction_id', self.transaction_id),
                         ('value', self.value),
                         ('mined', self.mined),
                         ('block_height', self.block_height),
                         ('address_id', self.address_id),
                         ('status', self.status),
                         ('meta', self.meta))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)


class TOKEN(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    currency_to_usd_rate = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float, nullable=False)
    token_to_usd_rate = db.Column(db.Float, nullable=False)
    token_value = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_sale_allocation = db.Column(db.Boolean, nullable=False, default=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), unique=True, nullable=False)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Relationships
    transaction = db.relationship(Transaction, back_populates="token_purchase")  # type: Transaction

    # Methods
    def as_dict(self):
        return {
            'id': self.id,
            'usd_value': self.usd_value,
            'token_value': self.token_value,
            'token_to_usd_rate': self.token_to_usd_rate,
            'currency_to_usd_rate': self.currency_to_usd_rate,
            'created': self.created,
        }

    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('currency_to_usd_rate', self.currency_to_usd_rate),
                         ('usd_value', self.usd_value),
                         ('token_to_usd_rate', self.token_to_usd_rate),
                         ('token_value', self.token_value),
                         ('active', self.active),
                         ('created', self.created),
                         ('transaction_id', self.transaction_id),
                         ('meta', self.meta))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)


class Price(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    fixed_currency = db.Column(db.String(10), nullable=False)
    variable_currency = db.Column(db.String(10), nullable=False)
    value = db.Column(db.Float, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('fixed_currency', self.fixed_currency),
                         ('variable_currency', self.variable_currency),
                         ('value', self.value),
                         ('created', self.created),
                         ('meta', self.meta))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)


class Withdraw(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(120), unique=False, nullable=True)
    to = db.Column(db.String(255), nullable=False, unique=False)
    value = db.Column(db.Float, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    mined = db.Column(db.DateTime, nullable=True)
    block_height = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=TransactionStatus.not_confirmed)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=False)

    # Relationships
    user = db.relationship(User, back_populates="withdraws")  # type: User

    # Methods
    def as_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'to': self.to,
            'value': self.value,
            'created': self.created,
            'mined': self.mined,
            'status': self.status,
        }

    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('transaction_id', self.transaction_id),
                         ('to', self.to),
                         ('value', self.value),
                         ('created', self.created),
                         ('mined', self.mined),
                         ('block_height', self.block_height),
                         ('address_id', self.address_id),
                         ('status', self.status),
                         ('meta', self.meta))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)


class Notification(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=False, nullable=True)
    type = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sended = db.Column(db.DateTime, nullable=True)
    is_sended = db.Column(db.Boolean, nullable=False, default=False)
    rendered_message = db.Column(db.Unicode, nullable=True)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Relationships
    user = db.relationship(User, back_populates="notifications")  # type: User

    meta_key_mailgun_message_id = 'mailgun_message_id'
    meta_key_mailgun_delivered = 'mailgun_delivered'
    meta_key_failed_notifications = 'failed_notifications'

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('user_id', self.transaction_id),
                         ('type', self.type),
                         ('email', self.email),
                         ('created', self.created),
                         ('sended', self.sended),
                         ('is_sended', self.is_sended),
                         ('meta', self.meta))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)

    def get_failed_notifications(self) -> Optional[int]:
        if self.meta_key_failed_notifications not in self.meta:
            return None
        return self.meta[self.meta_key_failed_notifications]

    def set_failed_notifications(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_failed_notifications] = value
        flag_modified(self, "meta")

    def get_mailgun_message_id(self) -> Optional[str]:
        if self.meta_key_mailgun_message_id not in self.meta:
            return None
        return self.meta[self.meta_key_mailgun_message_id]

    def set_mailgun_message_id(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_mailgun_message_id] = value
        flag_modified(self, "meta")

    def get_mailgun_delivered(self) -> Optional[str]:
        if self.meta_key_mailgun_delivered not in self.meta:
            return None
        return self.meta[self.meta_key_mailgun_delivered]

    def set_mailgun_delivered(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_mailgun_delivered] = value
        flag_modified(self, "meta")


class Affiliate(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=False, nullable=True)
    event = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(300), nullable=False, default='')
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sended = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Integer, nullable=True)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Meta keys
    meta_key_transaction_id = 'transaction_id'

    # Relationships
    user = db.relationship(User, back_populates="affiliates")  # type: User

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('user_id', self.user_id),
                         ('event', self.event),
                         ('url', self.url),
                         ('created', self.created),
                         ('sended', self.sended),
                         ('status', self.status))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)

    def get_transaction_id(self) -> Optional[int]:
        if self.meta_key_transaction_id not in self.meta:
            return None
        return self.meta[self.meta_key_transaction_id]

    def set_transaction_id(self, value: int):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_transaction_id] = value
        flag_modified(self, "meta")


class PresaleToken(db.Model):
    """
    TOKEN from presale round
    """
    __tablename__ = 'presale_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=False)
    token_value = db.Column(db.Float, nullable=False)
    currency_to_usd_rate = db.Column(db.Float, nullable=False, default=0)
    usd_value = db.Column(db.Float, nullable=False, default=0)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    comment = db.Column(db.String(32), nullable=False, default='ANGEL ROUND / PRESALE')
    is_sale_allocation = db.Column(db.Boolean)
    is_presale_round = db.Column(db.Boolean)

    # Relationships
    user = db.relationship(User, back_populates="presales")  # type: User


class UserTokenPrice(db.Model):
    """
    # 71 Custom TOKEN price for user
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    value = db.Column(db.Float, nullable=False)

    # Relationships
    user = db.relationship(User, back_populates="custom_token_prices")  # type: User

    class Meta:
        db_table = 'user_token_price'

    def __str__(self):
        return 'Custom Price for {}: {}$/TOKEN'.format(self.user.username, self.value)
