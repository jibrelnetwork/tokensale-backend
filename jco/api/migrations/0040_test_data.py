from datetime import datetime

from django.db import migrations, models
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from jco.api import models as jco_models
from jco.appdb import models as sa_models


def fill_test_data(apps, schema_editor):
    # create users
    user1 = User.objects.create_user('user1@main.com', 'user1@main.com', 'password1', last_login=datetime(2017, 11, 12))
    EmailAddress.objects.create(user=user1, email=user1.username, primary=True, verified=False)
    jco_models.Account.objects.create(user=user1)
    user2 = User.objects.create_user('user2@main.com', 'user2@main.com', 'password2', last_login=datetime(2017, 11, 12))
    EmailAddress.objects.create(user=user2, email=user2.username, primary=True, verified=False)
    jco_models.Account.objects.create(user=user2)

    # create addresses
    addr1 = jco_models.Address.objects.create(address='0x81b7e08f65bdf5648606c89998a9cc8164397648',
                                              type=sa_models.CurrencyType.eth,
                                              is_usable=True,
                                              user=user1)
    addr2 = jco_models.Address.objects.create(address='0x81b7e08f65bdf5648606c89998a9cc8164397649',
                                              type=sa_models.CurrencyType.eth,
                                              is_usable=True,
                                              user=user2)
    for i in range(0,30):
        jco_models.Address.objects.create(address='0x81b7e08f65bdf5648606c89998a9cc81643976{}'.format(50+i),
                                          type=sa_models.CurrencyType.eth,
                                          is_usable=True)
        jco_models.Address.objects.create(address='1Hz96kJKF2HLPGY{}JWLB5m9qGNxvt8tHJ'.format(16+i),
                                          type=sa_models.CurrencyType.btc,
                                          is_usable=True)

    # create transactions
    tr1 = jco_models.Transaction.objects.create(transaction_id='0x772e09623864367a51db758ed177398a9363b5889be94611ce2baafe2c357804',
                                                value=2.5,
                                                mined=datetime(2017, 11, 12),
                                                block_height=111,
                                                status='success',
                                                address=addr2)

    tr2 = jco_models.Transaction.objects.create(transaction_id='0x772e09623864367a51db758ed177398a9363b5889be94611ce2baafe2c357803',
                                                value=0.5,
                                                mined=datetime(2017, 11, 13),
                                                block_height=112,
                                                status='success',
                                                address=addr1)

    tr3 = jco_models.Transaction.objects.create(transaction_id='0x772e09623864367a51db758ed177398a9363b5889be94611ce2baafe2c357801',
                                                value=0.5,
                                                mined=datetime(2017, 11, 14),
                                                block_height=113,
                                                status='success',
                                                address=addr1)

    tr4 = jco_models.Transaction.objects.create(transaction_id='0x772e09623864367a51db758ed177398a9363b5889be94611ce2baafe2c357802',
                                                value=0.5,
                                                mined=datetime(2017, 11, 15),
                                                block_height=114,
                                                status='pending',
                                                address=addr1)

    # create bought tokens
    jco_models.Jnt.objects.create(jnt_value=150,
                                  currency_to_usd_rate=300.0,
                                  usd_value=150.0,
                                  jnt_to_usd_rate=1.0,
                                  active=True,
                                  created=datetime(2017, 11, 13),
                                  transaction=tr2)

    jco_models.Jnt.objects.create(jnt_value=150,
                                  currency_to_usd_rate=300.0,
                                  usd_value=150.0,
                                  jnt_to_usd_rate=1.0,
                                  active=True,
                                  created=datetime(2017, 11, 14),
                                  transaction=tr3)

    jco_models.Jnt.objects.create(jnt_value=1000,
                                  currency_to_usd_rate=400.0,
                                  usd_value=1000.0,
                                  jnt_to_usd_rate=1.0,
                                  active=True,
                                  created=datetime(2017, 11, 14),
                                  transaction=tr1)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0039_operation_last_notification_sent_at'),
    ]

    operations = [
        migrations.RunPython(fill_test_data),
    ]
