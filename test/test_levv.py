"""Tests for levv/main.py — getLogTemplate, calcPriority, filterLine."""

import re
import pytest
import levv


# ---------------------------------------------------------------------------
# getLogTemplate
# ---------------------------------------------------------------------------

class TestGetLogTemplate:

    def test_time_colon_returns_string(self):
        pattern = levv.getLogTemplate('time:')
        assert isinstance(pattern, str) and len(pattern) > 0

    def test_time_colon_is_valid_regex(self):
        pattern = levv.getLogTemplate('time:')
        re.compile(pattern)  # must not raise

    def test_pm2_returns_string(self):
        pattern = levv.getLogTemplate('pm2')
        assert isinstance(pattern, str) and len(pattern) > 0

    def test_pm2_is_valid_regex(self):
        pattern = levv.getLogTemplate('pm2')
        re.compile(pattern)  # must not raise

    def test_unknown_name_returns_none(self):
        assert levv.getLogTemplate('unknown') is None

    def test_empty_name_returns_none(self):
        assert levv.getLogTemplate('') is None

    def test_syslog_not_builtin(self):
        assert levv.getLogTemplate('syslog') is None


# ---------------------------------------------------------------------------
# calcPriority
# ---------------------------------------------------------------------------

class TestCalcPriority:

    def test_error_lowercase(self):
        assert levv.calcPriority('an error occurred') == 1

    def test_error_uppercase(self):
        assert levv.calcPriority('ERROR: disk full') == 1

    def test_error_mixed_case(self):
        assert levv.calcPriority('Error in subsystem') == 1

    def test_error_at_start_of_string(self):
        assert levv.calcPriority('error at position zero') == 1

    def test_error_embedded(self):
        assert levv.calcPriority('found error in log') == 1

    def test_warn_lowercase(self):
        assert levv.calcPriority('warning: low memory') == 2

    def test_warn_uppercase(self):
        assert levv.calcPriority('WARN: retrying') == 2

    def test_warn_word_boundary(self):
        assert levv.calcPriority('forwarding packets') == 6  # 'warn' not present

    def test_normal_message_returns_6(self):
        assert levv.calcPriority('service started successfully') == 6

    def test_empty_string_returns_6(self):
        assert levv.calcPriority('') == 6

    def test_error_takes_priority_over_warn(self):
        # 'error' check comes first in calcPriority
        assert levv.calcPriority('error and warning both present') == 1


# ---------------------------------------------------------------------------
# filterLine — empty / no-filter cases
# ---------------------------------------------------------------------------

class TestFilterLineEdgeCases:

    def test_empty_string_no_filter(self):
        r, s = levv.filterLine('', '')
        assert r == {} and s == ''

    def test_empty_string_with_filter(self):
        r, s = levv.filterLine(r'(?P<msg>.*)', '')
        assert r == {} and s == ''

    def test_non_empty_no_filter_passthrough(self):
        r, s = levv.filterLine('', 'hello world')
        assert r == {} and s == 'hello world'

    def test_non_matching_filter_returns_empty(self):
        r, s = levv.filterLine(r'^\d+', 'no digits here')
        assert r == {} and s == ''

    def test_invalid_regex_returns_empty(self):
        r, s = levv.filterLine(r'[invalid', 'some line')
        assert r == {} and s == ''


# ---------------------------------------------------------------------------
# filterLine — named groups
# ---------------------------------------------------------------------------

class TestFilterLineNamedGroups:

    def test_msg_group_extracted(self):
        r, s = levv.filterLine(r'(?P<msg>.*)', 'hello world')
        assert r['msg'] == 'hello world'
        assert s == 'hello world'

    def test_time_as_numeric_float(self):
        r, s = levv.filterLine(r'(?P<time>\d+\.\d+) (?P<msg>.*)', '1700000000.5 event')
        assert r['time'] == pytest.approx(1700000000.5)

    def test_time_as_integer_string(self):
        r, s = levv.filterLine(r'(?P<time>\d+) (?P<msg>.*)', '1700000000 event')
        assert r['time'] == pytest.approx(1700000000.0)

    def test_time_as_date_string_parsed(self):
        r, s = levv.filterLine(r'(?P<time>[^|]+)\|(?P<msg>.*)', '2023-06-15 12:00:00|event')
        assert 'time' in r
        assert isinstance(r['time'], float)
        assert r['time'] > 0

    def test_unparseable_time_removed_from_result(self):
        r, s = levv.filterLine(r'(?P<time>[^|]+)\|(?P<msg>.*)', 'not-a-date|event')
        assert 'time' not in r

    def test_sev_as_integer(self):
        r, s = levv.filterLine(r'(?P<sev>\d+) (?P<msg>.*)', '3 medium priority event')
        assert r['sev'] == 3

    def test_sev_non_integer_falls_back_to_calcpriority_on_message(self):
        # When sev can't be cast to int, calcPriority is called on the *message* text.
        # Message contains 'error', so priority = 1.
        r, s = levv.filterLine(r'(?P<sev>\w+) (?P<msg>.*)', 'LABEL critical error here')
        assert r['sev'] == 1

    def test_sev_non_integer_warn_in_message(self):
        r, s = levv.filterLine(r'(?P<sev>\w+) (?P<msg>.*)', 'LABEL memory warning issued')
        assert r['sev'] == 2

    def test_sev_non_integer_normal_message(self):
        r, s = levv.filterLine(r'(?P<sev>\w+) (?P<msg>.*)', 'INFO everything fine')
        assert r['sev'] == 6

    def test_all_three_named_groups(self):
        pattern = r'(?P<time>\d+) (?P<sev>\d+) (?P<msg>.*)'
        r, s = levv.filterLine(pattern, '1700000000 2 warn message')
        assert r['time'] == pytest.approx(1700000000.0)
        assert r['sev'] == 2
        assert r['msg'] == 'warn message'


# ---------------------------------------------------------------------------
# filterLine — positional (numbered) groups
# ---------------------------------------------------------------------------

class TestFilterLinePositionalGroups:

    def test_group1_used_as_msg(self):
        r, s = levv.filterLine(r'(\w+)', 'hello')
        assert r['msg'] == 'hello'

    def test_group1_msg_group2_time(self):
        r, s = levv.filterLine(r'(\w+) (\d+)', 'event 1700000000')
        assert r['msg'] == 'event'
        assert r['time'] == pytest.approx(1700000000.0)

    def test_group1_msg_group2_time_group3_sev(self):
        r, s = levv.filterLine(r'(\w+) (\d+) (\d+)', 'event 1700000000 3')
        assert r['msg'] == 'event'
        assert r['time'] == pytest.approx(1700000000.0)
        assert r['sev'] == 3


# ---------------------------------------------------------------------------
# filterLine — fractional-second groups (nsecs / usecs / msecs)
# ---------------------------------------------------------------------------

class TestFilterLineFractionalSeconds:

    def test_nsecs_added_to_time(self):
        pattern = r'(?P<time>\d+) (?P<nsecs>\d+) (?P<msg>.*)'
        r, s = levv.filterLine(pattern, '1700000000 500000000 event')
        assert r['time'] == pytest.approx(1700000000.5, abs=1e-6)

    def test_usecs_added_to_time(self):
        """Regression: usecs branch was erroneously reading g['nsecs']."""
        pattern = r'(?P<time>\d+) (?P<usecs>\d+) (?P<msg>.*)'
        r, s = levv.filterLine(pattern, '1700000000 500000 event')
        assert r['time'] == pytest.approx(1700000000.5, abs=1e-4)

    def test_msecs_added_to_time(self):
        """Regression: msecs branch was erroneously reading g['nsecs']."""
        pattern = r'(?P<time>\d+) (?P<msecs>\d+) (?P<msg>.*)'
        r, s = levv.filterLine(pattern, '1700000000 500 event')
        assert r['time'] == pytest.approx(1700000000.5, abs=1e-3)

    def test_usecs_without_nsecs_does_not_raise(self):
        """usecs branch must not KeyError when nsecs group is absent."""
        pattern = r'(?P<time>\d+) (?P<usecs>\d+) (?P<msg>.*)'
        r, s = levv.filterLine(pattern, '1700000000 123456 event')
        assert 'time' in r  # must survive without exception

    def test_msecs_without_nsecs_does_not_raise(self):
        """msecs branch must not KeyError when nsecs group is absent."""
        pattern = r'(?P<time>\d+) (?P<msecs>\d+) (?P<msg>.*)'
        r, s = levv.filterLine(pattern, '1700000000 250 event')
        assert 'time' in r


# ---------------------------------------------------------------------------
# filterLine — built-in templates
# ---------------------------------------------------------------------------

class TestFilterLineBuiltinTemplates:

    def test_time_colon_template_extracts_msg(self):
        r, s = levv.filterLine(levv.getLogTemplate('time:'),
                               '2023-06-15 12:00:00: server started')
        assert r['msg'] == 'server started'

    def test_time_colon_template_extracts_time(self):
        r, s = levv.filterLine(levv.getLogTemplate('time:'),
                               '2023-06-15 12:00:00: server started')
        assert 'time' in r
        assert isinstance(r['time'], float)

    def test_pm2_template_extracts_msg(self):
        r, s = levv.filterLine(levv.getLogTemplate('pm2'),
                               '1|appname | 2023-06-15 12:00:00: [ERR] Exception!')
        assert r['msg'] == '[ERR] Exception!'

    def test_pm2_template_extracts_sev(self):
        r, s = levv.filterLine(levv.getLogTemplate('pm2'),
                               '1|appname | 2023-06-15 12:00:00: [ERR] Exception!')
        assert r['sev'] == 1  # the '1' prefix is parsed as int

    def test_pm2_template_extracts_time(self):
        r, s = levv.filterLine(levv.getLogTemplate('pm2'),
                               '1|appname | 2023-06-15 12:00:00: [ERR] Exception!')
        assert 'time' in r
        assert isinstance(r['time'], float)
