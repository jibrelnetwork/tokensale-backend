from datetime import datetime
from unittest import mock
import pytz

from jco.api import models as m


@mock.patch('jco.api.models.now')
def test_get_current_state(mock_now, db):
    mock_now.return_value = datetime(2018, 8, 4)
    m.ICOState.objects.create(id='A', order=0, start_date=datetime(2018, 8, 1, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 3, tzinfo=pytz.utc))
    m.ICOState.objects.create(id='B', order=1, start_date=datetime(2018, 8, 3, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 5, tzinfo=pytz.utc))
    m.ICOState.objects.create(id='C', order=2, start_date=datetime(2018, 8, 5, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 7, tzinfo=pytz.utc))
    m.ICOState.objects.create(id='D', order=3, start_date=datetime(2018, 8, 7, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 8, tzinfo=pytz.utc))

    s = m.get_ico_current_state()
    assert s.id == 'B'


@mock.patch('jco.api.models.now')
def test_get_next_state(mock_now, db):
    mock_now.return_value = datetime(2018, 8, 4)
    m.ICOState.objects.create(id='A', order=0, start_date=datetime(2018, 8, 1, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 3, tzinfo=pytz.utc))
    m.ICOState.objects.create(id='B', order=1, start_date=datetime(2018, 8, 3, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 5, tzinfo=pytz.utc))
    m.ICOState.objects.create(id='C', order=2, start_date=datetime(2018, 8, 5, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 7, tzinfo=pytz.utc))
    m.ICOState.objects.create(id='D', order=3, start_date=datetime(2018, 8, 7, tzinfo=pytz.utc),
                              finish_date=datetime(2018, 8, 8, tzinfo=pytz.utc))

    s = m.get_ico_next_state()
    assert s.id == 'C'
