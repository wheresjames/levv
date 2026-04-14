"""Tests for levv/formats/ — all format modules and the registry."""

import time
import json
import pytest

import levv
import levv.formats as formats
from levv.formats import utils, detect_format, parse_line, list_formats
from levv.formats import (
    text, date, kmsg, www, auto,
    syslog, journald, docker, json_lines, logfmt,
    nginx_error, python_log, log4j,
)


# ===========================================================================
# utils
# ===========================================================================

class TestFindDate:

    def test_iso_datetime_found(self):
        length, d = utils.findDate('2023-06-15 12:00:00 some message')
        assert length > 0 and d != 0

    def test_message_follows_date(self):
        txt = '2023-06-15 12:00:00 some message'
        length, _ = utils.findDate(txt)
        assert 'some message' in txt[length:]

    def test_no_date_returns_zero(self):
        length, d = utils.findDate('no date whatsoever')
        assert length == 0 and d == 0

    def test_empty_returns_zero(self):
        assert utils.findDate('') == (0, 0)


class TestCalcPriority:

    def test_error_returns_1(self):
        assert utils.calcPriority('an error occurred') == 1

    def test_fatal_returns_1(self):
        assert utils.calcPriority('FATAL: process died') == 1

    def test_critical_returns_1(self):
        assert utils.calcPriority('critical failure') == 1

    def test_warn_returns_2(self):
        assert utils.calcPriority('WARNING: low memory') == 2

    def test_notice_returns_5(self):
        assert utils.calcPriority('notice: config reloaded') == 5

    def test_normal_returns_6(self):
        assert utils.calcPriority('service started') == 6

    def test_empty_returns_6(self):
        assert utils.calcPriority('') == 6

    def test_error_beats_warn(self):
        assert utils.calcPriority('error and warning') == 1


class TestParseTimeStr:

    def test_float_string(self):
        ts = time.time() - 30
        assert utils.parse_time_str(str(ts)) == pytest.approx(ts, abs=1.0)

    def test_iso_date_string(self):
        t = utils.parse_time_str('2023-06-15 12:00:00')
        assert t is not None and t > 0

    def test_invalid_returns_none(self):
        assert utils.parse_time_str('not-a-time') is None

    def test_none_input_returns_none(self):
        assert utils.parse_time_str(None) is None


# ===========================================================================
# text
# ===========================================================================

class TestText:

    def test_probe_returns_zero(self):
        assert text.probe('anything') == 0.0

    def test_parse_uses_current_time(self):
        before = time.time()
        r = text.parse('hello world')
        after = time.time()
        assert before <= r['time'] <= after

    def test_parse_preserves_message(self):
        assert text.parse('hello world')['msg'] == 'hello world'

    def test_parse_empty_returns_empty(self):
        assert text.parse('') == {}


# ===========================================================================
# date
# ===========================================================================

class TestDate:

    def test_probe_iso_date(self):
        assert date.probe('2023-06-15 12:00:00 message') > 0

    def test_probe_non_date_zero(self):
        assert date.probe('plain text message') == 0.0

    def test_parse_extracts_time(self):
        r = date.parse('2023-06-15 12:00:00 server started')
        assert 'time' in r and isinstance(r['time'], float)

    def test_parse_extracts_message(self):
        r = date.parse('2023-06-15 12:00:00 server started')
        assert 'server started' in r['msg']

    def test_parse_severity_from_message(self):
        r = date.parse('2023-06-15 12:00:00 error detected')
        assert r['sev'] == 1

    def test_parse_no_date_returns_empty(self):
        assert date.parse('no date here') == {}

    def test_parse_empty_returns_empty(self):
        assert date.parse('') == {}


# ===========================================================================
# kmsg
# ===========================================================================

class TestKmsg:

    VALID = '6,339,5085350,-;NET: Registered PF_ALG protocol family'

    def test_probe_valid(self):
        assert kmsg.probe(self.VALID) > 0.5

    def test_probe_invalid(self):
        assert kmsg.probe('plain log line') == 0.0

    def test_parse_keys(self):
        r = kmsg.parse(self.VALID)
        assert {'sev', 'seq', 'time', 'msg'} <= r.keys()

    def test_parse_sev(self):
        assert kmsg.parse(self.VALID)['sev'] == '6'

    def test_parse_time_positive(self):
        assert kmsg.parse(self.VALID)['time'] > 0

    def test_parse_message(self):
        assert 'NET: Registered PF_ALG protocol family' in kmsg.parse(self.VALID)['msg']

    def test_parse_too_few_fields(self):
        assert kmsg.parse('6,339') == {}


# ===========================================================================
# www
# ===========================================================================

class TestWww:

    def _line(self, status, path='/', sz='1024'):
        return (f'127.0.0.1 - - [01/Jan/2024:00:00:00 +0000]'
                f' "GET {path} HTTP/1.1" {status} {sz}')

    def test_probe_valid(self):
        assert www.probe(self._line(200)) > 0.5

    def test_probe_non_clf(self):
        assert www.probe('plain log line') == 0.0

    def test_http_200_sev_6(self):
        assert www.parse(self._line(200))['sev'] == 6

    def test_http_404_sev_2(self):
        assert www.parse(self._line(404))['sev'] == 2

    def test_http_500_sev_1(self):
        assert www.parse(self._line(500))['sev'] == 1

    def test_http_301_sev_3(self):
        assert www.parse(self._line(301))['sev'] == 3

    def test_message_contains_ip(self):
        assert '127.0.0.1' in www.parse(self._line(200))['msg']

    def test_too_short_returns_empty(self):
        assert www.parse('127.0.0.1 - -') == {}


# ===========================================================================
# auto
# ===========================================================================

class TestAuto:

    def test_probe_returns_zero(self):
        assert auto.probe('anything') == 0.0

    def test_unix_timestamp(self):
        ts = time.time() - 60
        r = auto.parse(f'{ts} test message')
        assert r['time'] == pytest.approx(ts, abs=1.0)
        assert r['msg'] == 'test message'

    def test_unix_timestamp_with_priority(self):
        ts = time.time() - 60
        r = auto.parse(f'{ts} 3 some message')
        assert r['sev'] == 3

    def test_date_fallback(self):
        r = auto.parse('2023-06-15 12:00:00 server started')
        assert 'time' in r and isinstance(r['time'], float)

    def test_plain_text_uses_now(self):
        before = time.time()
        r = auto.parse('completely plain log line')
        after = time.time()
        assert before <= r['time'] <= after

    def test_empty_returns_empty(self):
        assert auto.parse('') == {}

    def test_old_timestamp_not_used(self):
        r = auto.parse('1000000 old timestamp message')
        assert r['time'] != pytest.approx(1000000, abs=1.0)


# ===========================================================================
# syslog
# ===========================================================================

class TestSyslog:

    BSD = 'Jan 15 10:23:01 myhost sshd[1234]: Failed password for root'
    RFC5424 = ('<34>1 2024-01-15T10:23:01.000Z myhost sshd 1234 - - '
               'Failed password for root')
    PRI = '<34>Jan 15 10:23:01 myhost sshd[1234]: Failed password for root'

    def test_probe_bsd(self):
        assert syslog.probe(self.BSD) > 0.5

    def test_probe_rfc5424(self):
        assert syslog.probe(self.RFC5424) > 0.5

    def test_probe_pri(self):
        assert syslog.probe(self.PRI) > 0.5

    def test_probe_non_syslog(self):
        assert syslog.probe('plain text line') == 0.0

    def test_parse_bsd_has_time(self):
        r = syslog.parse(self.BSD)
        assert 'time' in r and isinstance(r['time'], float)

    def test_parse_bsd_has_msg(self):
        r = syslog.parse(self.BSD)
        assert 'Failed password for root' in r['msg']

    def test_parse_rfc5424_has_time(self):
        r = syslog.parse(self.RFC5424)
        assert 'time' in r and r['time'] > 0

    def test_parse_rfc5424_severity(self):
        # PRI=34 → facility=4, severity=2 (crit) → maps to sev 1
        r = syslog.parse(self.RFC5424)
        assert r['sev'] in (1, 2)

    def test_parse_non_syslog_returns_empty(self):
        assert syslog.parse('plain text') == {}


# ===========================================================================
# journald
# ===========================================================================

class TestJournald:

    ISO = '2024-01-15T10:23:01+0000 myhost systemd[1]: Started network.'

    def test_probe_iso(self):
        assert journald.probe(self.ISO) > 0.5

    def test_probe_non_journald(self):
        assert journald.probe('plain text') == 0.0

    def test_parse_time(self):
        r = journald.parse(self.ISO)
        assert 'time' in r and r['time'] > 0

    def test_parse_msg_contains_unit(self):
        r = journald.parse(self.ISO)
        assert 'systemd' in r['msg']

    def test_parse_non_journald_returns_empty(self):
        assert journald.parse('plain text') == {}


# ===========================================================================
# docker
# ===========================================================================

class TestDocker:

    LINE = '2024-01-15T10:23:01.123456789Z stdout F application started'
    STDERR = '2024-01-15T10:23:01.000Z stderr F connection refused'

    def test_probe_valid(self):
        assert docker.probe(self.LINE) > 0.5

    def test_probe_non_docker(self):
        assert docker.probe('plain text') == 0.0

    def test_parse_time(self):
        r = docker.parse(self.LINE)
        assert 'time' in r and r['time'] > 0

    def test_parse_msg(self):
        r = docker.parse(self.LINE)
        assert r['msg'] == 'application started'

    def test_stderr_bumps_severity(self):
        r = docker.parse(self.STDERR)
        assert r['sev'] <= 2  # stderr + no keyword → sev 2

    def test_parse_non_docker_returns_empty(self):
        assert docker.parse('plain text') == {}


# ===========================================================================
# json_lines
# ===========================================================================

class TestJsonLines:

    def _line(self, **kw):
        return json.dumps(kw)

    def test_probe_valid_json(self):
        assert json_lines.probe(self._line(message='hello', level='info')) > 0.5

    def test_probe_non_json(self):
        assert json_lines.probe('plain text') == 0.0

    def test_probe_json_array_zero(self):
        assert json_lines.probe('[1, 2, 3]') == 0.0

    def test_parse_message_key(self):
        r = json_lines.parse(self._line(message='hello world', level='info'))
        assert r['msg'] == 'hello world'

    def test_parse_msg_key(self):
        r = json_lines.parse(self._line(msg='hello world'))
        assert r['msg'] == 'hello world'

    def test_parse_level_info_sev_6(self):
        r = json_lines.parse(self._line(msg='ok', level='info'))
        assert r['sev'] == 6

    def test_parse_level_error_sev_1(self):
        r = json_lines.parse(self._line(msg='boom', level='error'))
        assert r['sev'] == 1

    def test_parse_level_warn_sev_2(self):
        r = json_lines.parse(self._line(msg='slow', level='warn'))
        assert r['sev'] == 2

    def test_parse_iso_timestamp(self):
        r = json_lines.parse(self._line(
            timestamp='2024-01-15T10:23:01Z', msg='event'))
        assert r['time'] > 0

    def test_parse_unix_timestamp(self):
        ts = time.time()
        r = json_lines.parse(self._line(ts=ts, msg='event'))
        assert r['time'] == pytest.approx(ts, abs=1.0)

    def test_parse_ms_timestamp_converted(self):
        ts = time.time()
        r = json_lines.parse(self._line(ts=ts * 1000, msg='event'))
        assert r['time'] == pytest.approx(ts, abs=1.0)

    def test_parse_no_message_falls_back_to_raw(self):
        line = '{"code": 42}'
        r = json_lines.parse(line)
        assert r['msg'] == line

    def test_parse_non_json_returns_empty(self):
        assert json_lines.parse('not json') == {}


# ===========================================================================
# logfmt
# ===========================================================================

class TestLogfmt:

    VALID = 'time=2024-01-15T10:23:01Z level=info msg="request handled" path=/api'

    def test_probe_valid(self):
        assert logfmt.probe(self.VALID) > 0.5

    def test_probe_non_logfmt(self):
        assert logfmt.probe('plain text message') == 0.0

    def test_parse_message(self):
        r = logfmt.parse(self.VALID)
        assert r['msg'] == 'request handled'

    def test_parse_time(self):
        r = logfmt.parse(self.VALID)
        assert r['time'] > 0

    def test_parse_severity_info(self):
        r = logfmt.parse(self.VALID)
        assert r['sev'] == 6

    def test_parse_severity_error(self):
        r = logfmt.parse('level=error msg="disk full" time=2024-01-15T10:23:01Z')
        assert r['sev'] == 1

    def test_parse_quoted_value(self):
        r = logfmt.parse('msg="hello world" level=info')
        assert r['msg'] == 'hello world'

    def test_parse_empty_returns_empty(self):
        assert logfmt.parse('') == {}


# ===========================================================================
# nginx_error
# ===========================================================================

class TestNginxError:

    LINE = '2024/01/15 10:23:01 [error] 1234#5678: *99 connect() failed'
    WARN = '2024/01/15 10:23:01 [warn] 1234#5678: *99 slow response'

    def test_probe_valid(self):
        assert nginx_error.probe(self.LINE) > 0.5

    def test_probe_non_nginx(self):
        assert nginx_error.probe('plain text') == 0.0

    def test_parse_time(self):
        r = nginx_error.parse(self.LINE)
        assert 'time' in r and r['time'] > 0

    def test_parse_error_sev(self):
        assert nginx_error.parse(self.LINE)['sev'] == 1

    def test_parse_warn_sev(self):
        assert nginx_error.parse(self.WARN)['sev'] == 2

    def test_parse_msg(self):
        assert 'connect() failed' in nginx_error.parse(self.LINE)['msg']

    def test_parse_non_nginx_returns_empty(self):
        assert nginx_error.parse('plain text') == {}


# ===========================================================================
# python_log
# ===========================================================================

class TestPythonLog:

    DEFAULT = '2024-01-15 10:23:01,123 ERROR myapp.module: connection lost'
    INFO    = '2024-01-15 10:23:01,000 INFO  myapp: started'
    EXTENDED = '2024-01-15 10:23:01,123 - myapp.module - ERROR - connection lost'

    def test_probe_default(self):
        assert python_log.probe(self.DEFAULT) > 0.5

    def test_probe_extended(self):
        assert python_log.probe(self.EXTENDED) > 0.5

    def test_probe_non_python(self):
        assert python_log.probe('plain text') == 0.0

    def test_parse_error_sev(self):
        assert python_log.parse(self.DEFAULT)['sev'] == 1

    def test_parse_info_sev(self):
        assert python_log.parse(self.INFO)['sev'] == 6

    def test_parse_msg(self):
        assert 'connection lost' in python_log.parse(self.DEFAULT)['msg']

    def test_parse_time(self):
        assert python_log.parse(self.DEFAULT)['time'] > 0

    def test_parse_non_python_returns_empty(self):
        assert python_log.parse('plain text') == {}


# ===========================================================================
# log4j
# ===========================================================================

class TestLog4j:

    FULL   = '2024-01-15 10:23:01,123 ERROR [main] com.example.App - NullPointerException'
    SIMPLE = '2024-01-15 10:23:01,123 WARN  com.example.App - slow query'

    def test_probe_full(self):
        assert log4j.probe(self.FULL) > 0.5

    def test_probe_simple(self):
        assert log4j.probe(self.SIMPLE) > 0.5

    def test_probe_non_log4j(self):
        assert log4j.probe('plain text') == 0.0

    def test_parse_error_sev(self):
        assert log4j.parse(self.FULL)['sev'] == 1

    def test_parse_warn_sev(self):
        assert log4j.parse(self.SIMPLE)['sev'] == 2

    def test_parse_msg(self):
        assert 'NullPointerException' in log4j.parse(self.FULL)['msg']

    def test_parse_time(self):
        assert log4j.parse(self.FULL)['time'] > 0

    def test_parse_non_log4j_returns_empty(self):
        assert log4j.parse('plain text') == {}


# ===========================================================================
# Registry and dispatch
# ===========================================================================

class TestRegistry:

    def test_all_formats_registered(self):
        for name in ('text', 'date', 'kmsg', 'www', 'auto',
                     'syslog', 'journald', 'docker', 'json',
                     'logfmt', 'nginx-error', 'python', 'log4j'):
            assert name in formats.REGISTRY

    def test_list_formats_returns_tuples(self):
        result = list_formats()
        assert all(isinstance(n, str) and isinstance(d, str) for n, d in result)

    def test_parse_line_json(self):
        line = json.dumps({'msg': 'hello', 'level': 'info'})
        r = parse_line('json', line)
        assert r['msg'] == 'hello'

    def test_parse_line_unknown_falls_back_to_auto(self):
        ts = time.time() - 30
        r = parse_line('nonexistent', f'{ts} event')
        assert r['time'] == pytest.approx(ts, abs=1.0)

    def test_parse_line_empty_format_uses_auto(self):
        ts = time.time() - 30
        r = parse_line('', f'{ts} event')
        assert r['time'] == pytest.approx(ts, abs=1.0)


# ===========================================================================
# detect_format
# ===========================================================================

class TestDetectFormat:

    def _sample(self, lines):
        return lines

    def test_detects_json(self):
        sample = [json.dumps({'msg': f'event {i}', 'level': 'info'}) for i in range(10)]
        assert detect_format(sample) == 'json'

    def test_detects_nginx_error(self):
        sample = [f'2024/01/15 10:23:0{i} [error] 1{i}#0: *1 failed' for i in range(5)]
        assert detect_format(sample) == 'nginx-error'

    def test_detects_python_log(self):
        sample = [f'2024-01-15 10:23:0{i},123 INFO myapp: started' for i in range(5)]
        assert detect_format(sample) == 'python'

    def test_detects_log4j(self):
        sample = [f'2024-01-15 10:23:0{i},123 INFO [main] com.App - msg' for i in range(5)]
        assert detect_format(sample) == 'log4j'

    def test_detects_www(self):
        sample = [
            f'127.0.0.{i} - - [01/Jan/2024:00:00:00 +0000] "GET / HTTP/1.1" 200 512'
            for i in range(1, 6)
        ]
        assert detect_format(sample) == 'www'

    def test_detects_docker(self):
        sample = [f'2024-01-15T10:23:0{i}Z stdout F message {i}' for i in range(5)]
        assert detect_format(sample) == 'docker'

    def test_falls_back_to_auto_on_plain_text(self):
        sample = ['just some plain log lines'] * 10
        assert detect_format(sample) == 'auto'

    def test_empty_sample_returns_auto(self):
        assert detect_format([]) == 'auto'

    def test_extension_hint_syslog(self):
        # BSD syslog lines — also resembles journald short; extension tips it
        sample = ['Jan 15 10:23:01 host proc[1]: message'] * 5
        result = detect_format(sample, filename='/var/log/syslog')
        assert result in ('syslog', 'journald')  # both are valid; hint helps

    def test_json_extension_hint(self):
        sample = [json.dumps({'msg': 'event', 'level': 'info'})] * 5
        assert detect_format(sample, filename='app.json') == 'json'


# ===========================================================================
# levv public API re-exports
# ===========================================================================

class TestLevvPublicAPI:
    """Verify that levv.xxx still works for all previously-public symbols."""

    def test_calcPriority_accessible(self):
        assert levv.calcPriority('error') == 1

    def test_findDate_accessible(self):
        length, d = levv.findDate('2023-06-15 12:00:00 msg')
        assert length > 0

    def test_parse_line_accessible(self):
        r = levv.parse_line('text', 'hello')
        assert r['msg'] == 'hello'

    def test_detect_format_accessible(self):
        sample = [json.dumps({'msg': 'x', 'level': 'info'})] * 5
        assert levv.detect_format(sample) == 'json'

    def test_list_formats_accessible(self):
        assert len(levv.list_formats()) > 5
