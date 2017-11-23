from datetime import datetime
from typing import List, Optional

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.attributes import flag_modified

from jco.appdb.db import db


class CurrencyType:
    jnt = 'JNT'
    btc = 'BTC'
    eth = 'ETH'
    usd = 'USD'
    eur = 'EUR'
    chf = 'CHF'


class TransactionStatus:
    pending = 'pending'
    fail = 'fail'
    success = 'success'


class User(db.Model):
    """
    Django auth user
    """

    __tablename__ = 'auth_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)

    addresses = db.relationship('Address',
                                back_populates="user",
                                cascade="all, delete-orphan",
                                passive_deletes=True)  # type: Address

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('fullname', self.fullname),
                         ('email', self.email),
                         ('country', self.country),
                         ('citizenship', self.citizenship),
                         ('created', self.created),
                         ('notified', self.notified),
                         ('docs_received', self.docs_received))

        argsString = ', '.join(['{}={}'.format(f[0], '"' + f[1] + '"' if (type(f[1]) == str) else f[1])
                                for f in fieldsToPrint])
        return '<{}({})>'.format(self.__class__.__name__, argsString)

    def as_dict(self):
        return {
            'id': self.id,
            'fullname': self.fullname,
            'email': self.email,
            'country': self.country,
            'citizenship': self.citizenship,
            'created': self.created,
            'notified': self.notified,
            'docs_received': self.docs_received
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
    docs_received = db.Column(db.Boolean, nullable=False, default=False)
    notified = db.Column(db.Boolean, nullable=False, default=False)
    is_identity_verified = db.Column(db.Boolean, nullable=False, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=True)
    etherium_address = db.Column(db.String(255), nullable=False, default='')

    document_url = db.Column(db.String(00), nullable=False, default='')
    #user = db.relationship(User, back_populates="accountes")  # type: User

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('fullname', self.fullname),
                         ('email', self.email),
                         ('country', self.country),
                         ('citizenship', self.citizenship),
                         ('created', self.created),
                         ('notified', self.notified),
                         ('docs_received', self.docs_received))

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
            'docs_received': self.docs_received
        }


class Address(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    is_usable = db.Column(db.Boolean, nullable=False, default=True)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})
    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'), unique=True)
    user = db.relationship(User, back_populates="addresses")  # type: User

    # Relationships
    transactions = db.relationship('Transaction',
                                   back_populates="address",
                                   cascade="all, delete-orphan",
                                   passive_deletes=True,
                                   order_by='Transaction.id')  # type: List[Transaction]

    withdraws = db.relationship('Withdraw',
                                back_populates="address",
                                cascade="all, delete-orphan",
                                passive_deletes=True,
                                order_by='Withdraw.id')  # type: List[Withdraw]

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
    jnt_purchase = db.relationship('JNT',
                                   back_populates="transaction",
                                   cascade="all, delete-orphan",
                                   passive_deletes=True,
                                   uselist=False)  # type: JNT

    # Meta keys
    meta_key_notified = 'notified'
    meta_key_failed_notifications = 'failed_notifications'
    meta_key_mailgun_message_id = 'mailgun_message_id'
    meta_key_mailgun_delivered = 'mailgun_delivered'
    meta_key_skip_jnt_calculation = 'skip_jnt_calculation'

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
            'mailgun_delivered': self.get_mailgun_delivered()
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

    def get_skip_jnt_calculation(self) -> Optional[bool]:
        if self.meta_key_skip_jnt_calculation not in self.meta:
            return None
        return self.meta[self.meta_key_skip_jnt_calculation]

    def set_skip_jnt_calculation(self, value: bool):
        if self.meta is None:
            self.meta = {}
        self.meta[self.meta_key_skip_jnt_calculation] = value
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


class JNT(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.String(64), unique=True, nullable=False)
    currency_to_usd_rate = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float, nullable=False)
    jnt_to_usd_rate = db.Column(db.Float, nullable=False)
    jnt_value = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), unique=True, nullable=False)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Relationships
    transaction = db.relationship(Transaction, back_populates="jnt_purchase")  # type: Transaction

    # Methods
    def __repr__(self):
        fieldsToPrint = (('id', self.id),
                         ('purchase_id', self.purchase_id),
                         ('currency_to_usd_rate', self.currency_to_usd_rate),
                         ('usd_value', self.usd_value),
                         ('jnt_to_usd_rate', self.jnt_to_usd_rate),
                         ('jnt_value', self.jnt_value),
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
    transaction_id = db.Column(db.String(120), unique=False)
    to = db.Column(db.String(255), nullable=False, unique=False)
    value = db.Column(db.Float, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    mined = db.Column(db.DateTime, nullable=True)
    block_height = db.Column(db.Integer, nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False, default=TransactionStatus.pending)
    meta = db.Column(JSONB, nullable=False, default=lambda: {})

    # Relationships
    address = db.relationship(Address, back_populates="withdraws")  # type: Address

    # Methods
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
