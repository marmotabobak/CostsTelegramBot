import pytest
from unittest.mock import Mock
import datetime

import funcs


@pytest.fixture
def make_2000_02_15_now():
    funcs.datetime_now = Mock(return_value=datetime.datetime(year=2000, month=2, day=15))


def test_first_day_of_current_month(make_2000_02_15_now):
    assert funcs.first_day_of_current_month() == datetime.datetime(2000, 2, 1)


def test_first_day_of_next_month(make_2000_02_15_now):
    assert funcs.first_day_of_next_month() == datetime.datetime(2000, 3, 1)
    funcs.datetime_now = Mock(return_value=datetime.datetime(year=2000, month=12, day=15))
    assert funcs.first_day_of_next_month() == datetime.datetime(2001, 1, 1)


def test_first_day_of_last_month(make_2000_02_15_now):
    assert funcs.first_day_of_last_month() == datetime.datetime(2000, 1, 1)
    funcs.datetime_now = Mock(return_value=datetime.datetime(year=2000, month=1, day=15))
    assert funcs.first_day_of_last_month() == datetime.datetime(1999, 12, 1)


def test_last_day_of_current_month(make_2000_02_15_now):
    assert funcs.last_day_of_current_month() == datetime.datetime(2000, 2, 29)
    funcs.datetime_now = Mock(return_value=datetime.datetime(year=2001, month=2, day=15))
    assert funcs.last_day_of_current_month() == datetime.datetime(2001, 2, 28)


def test_last_day_of_last_month(make_2000_02_15_now):
    assert funcs.last_day_of_last_month() == datetime.datetime(2000, 1, 31)
    funcs.datetime_now = Mock(return_value=datetime.datetime(year=2000, month=1, day=15))
    assert funcs.last_day_of_last_month() == datetime.datetime(1999, 12, 31)


def test_num_with_delimiters():
    assert funcs.num_with_delimiters(100_000, ',') == '100,000'
    assert funcs.num_with_delimiters(1234567, '.') == '1.234.567'
    assert funcs.num_with_delimiters(1023) == '1 023'
    assert funcs.num_with_delimiters(-1234.234, '_') == '-1_234.234'
    with pytest.raises(ValueError):
        funcs.num_with_delimiters('1000')
    with pytest.raises(TypeError):
        funcs.num_with_delimiters()


def test_get_month_name():
    months = ('январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
             'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь')
    for month_idx in range(len(months)):
        assert funcs.get_month_name(month_idx + 1) == months[month_idx]
    for val in (13, ''):
        with pytest.raises(ValueError):
            funcs.get_month_name(val)
    with pytest.raises(TypeError):
        funcs.get_month_name()


