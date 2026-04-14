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
    w3c_ext, haproxy, apache_error, postgresql, logcat,
    gelf, cef, mysql_error, kubernetes, traefik, csv_log,
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
                     'logfmt', 'nginx-error', 'python', 'log4j',
                     'w3c', 'haproxy', 'apache-error', 'postgresql', 'logcat',
                     'gelf', 'cef', 'mysql', 'k8s', 'traefik', 'csv'):
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


# ===========================================================================
# w3c_ext
# ===========================================================================

class TestW3cExt:

    FIELDS = '#Fields: date time c-ip cs-method cs-uri-stem sc-status sc-bytes'
    DATA   = '2024-01-15 10:23:45 10.0.0.1 GET /index.html 200 1234'

    def setup_method(self):
        w3c_ext._fields = []

    def test_probe_fields_directive(self):
        assert w3c_ext.probe(self.FIELDS) > 0.5

    def test_probe_version_directive(self):
        assert w3c_ext.probe('#Version: 1.0') > 0.5

    def test_probe_data_line(self):
        assert w3c_ext.probe(self.DATA) > 0.5

    def test_probe_non_w3c(self):
        assert w3c_ext.probe('plain text') == 0.0

    def test_fields_directive_sets_state(self):
        w3c_ext.parse(self.FIELDS)
        assert w3c_ext._fields == ['date', 'time', 'c-ip', 'cs-method',
                                    'cs-uri-stem', 'sc-status', 'sc-bytes']

    def test_parse_with_header_then_data(self):
        w3c_ext.parse(self.FIELDS)
        r = w3c_ext.parse(self.DATA)
        assert r['time'] > 0
        assert r['sev'] == 6
        assert '10.0.0.1' in r['msg']
        assert 'GET' in r['msg']

    def test_parse_status_500_sev_1(self):
        w3c_ext.parse(self.FIELDS)
        r = w3c_ext.parse('2024-01-15 10:23:45 10.0.0.1 GET /crash.php 500 0')
        assert r['sev'] == 1

    def test_parse_status_404_sev_2(self):
        w3c_ext.parse(self.FIELDS)
        r = w3c_ext.parse('2024-01-15 10:23:45 10.0.0.1 GET /nope 404 0')
        assert r['sev'] == 2

    def test_parse_directive_returns_empty(self):
        assert w3c_ext.parse('#Date: 2024-01-15') == {}

    def test_parse_empty_returns_empty(self):
        assert w3c_ext.parse('') == {}


# ===========================================================================
# haproxy
# ===========================================================================

class TestHaproxy:

    LINE = ('10.0.0.1:56789 [15/Jan/2024:10:23:45.123] '
            'frontend backend/server 0/0/1/2/3 200 1234 - - ---- 5/5/3/1/0 0/0 '
            '"GET /path HTTP/1.1"')
    SYSLOG = ('Jan 15 10:23:45 host haproxy[1234]: 10.0.0.1:56789 '
              '[15/Jan/2024:10:23:45.123] fe be/srv 0/0/1/2/3 500 0 - - ---- 1/1/0/0/0 0/0 '
              '"POST /api HTTP/1.1"')

    def test_probe_direct(self):
        assert haproxy.probe(self.LINE) > 0.5

    def test_probe_syslog_prefixed(self):
        assert haproxy.probe(self.SYSLOG) > 0.5

    def test_probe_non_haproxy(self):
        assert haproxy.probe('plain text') == 0.0

    def test_parse_time(self):
        r = haproxy.parse(self.LINE)
        assert r['time'] > 0

    def test_parse_200_sev_6(self):
        assert haproxy.parse(self.LINE)['sev'] == 6

    def test_parse_500_sev_1(self):
        assert haproxy.parse(self.SYSLOG)['sev'] == 1

    def test_parse_msg_contains_client(self):
        assert '10.0.0.1' in haproxy.parse(self.LINE)['msg']

    def test_parse_non_haproxy_returns_empty(self):
        assert haproxy.parse('plain text') == {}


# ===========================================================================
# apache_error
# ===========================================================================

class TestApacheError:

    V24   = '[Mon Jan 15 10:23:45.123456 2024] [core:error] [pid 1234] AH00124: msg'
    PRE24 = '[Mon Jan 15 10:23:45 2024] [error] [client 10.0.0.1] permission denied'
    WARN  = '[Mon Jan 15 10:23:45 2024] [warn] [client 10.0.0.1] slow request'

    def test_probe_v24(self):
        assert apache_error.probe(self.V24) > 0.5

    def test_probe_pre24(self):
        assert apache_error.probe(self.PRE24) > 0.5

    def test_probe_non_apache(self):
        assert apache_error.probe('plain text') == 0.0

    def test_parse_v24_time(self):
        assert apache_error.parse(self.V24)['time'] > 0

    def test_parse_v24_sev_error(self):
        assert apache_error.parse(self.V24)['sev'] == 1

    def test_parse_pre24_sev_warn(self):
        assert apache_error.parse(self.WARN)['sev'] == 2

    def test_parse_pre24_msg(self):
        assert 'permission denied' in apache_error.parse(self.PRE24)['msg']

    def test_parse_non_apache_returns_empty(self):
        assert apache_error.parse('plain text') == {}


# ===========================================================================
# postgresql
# ===========================================================================

class TestPostgresql:

    LOG  = '2024-01-15 10:23:45.123 UTC [1234] LOG:  database system is ready'
    ERR  = '2024-01-15 10:23:45.123 UTC [1234] ERROR:  relation "foo" does not exist'
    WARN = '2024-01-15 10:23:45.123 UTC [1234] WARNING:  transaction timeout'
    USER = '2024-01-15 10:23:45.123 UTC [1234] postgres@mydb LOG:  checkpoint complete'

    def test_probe_log(self):
        assert postgresql.probe(self.LOG) > 0.5

    def test_probe_error(self):
        assert postgresql.probe(self.ERR) > 0.5

    def test_probe_user_at_db(self):
        assert postgresql.probe(self.USER) > 0.5

    def test_probe_non_pg(self):
        assert postgresql.probe('plain text') == 0.0

    def test_parse_time(self):
        assert postgresql.parse(self.LOG)['time'] > 0

    def test_parse_log_sev_6(self):
        assert postgresql.parse(self.LOG)['sev'] == 6

    def test_parse_error_sev_1(self):
        assert postgresql.parse(self.ERR)['sev'] == 1

    def test_parse_warning_sev_2(self):
        assert postgresql.parse(self.WARN)['sev'] == 2

    def test_parse_msg_contains_pid(self):
        assert 'pid:1234' in postgresql.parse(self.LOG)['msg']

    def test_parse_non_pg_returns_empty(self):
        assert postgresql.parse('plain text') == {}


# ===========================================================================
# logcat
# ===========================================================================

class TestLogcat:

    THREADTIME = '01-15 10:23:45.123  1234  5678 D MyTag: some debug message'
    WITH_YEAR  = '2024-01-15 10:23:45.123  1234  5678 E MyTag: crash here'
    BRIEF      = 'E/MyTag(1234): NullPointerException'
    WARN       = '01-15 10:23:45.123  1234  5678 W NetworkTag: slow response'

    def test_probe_threadtime(self):
        assert logcat.probe(self.THREADTIME) > 0.5

    def test_probe_brief(self):
        assert logcat.probe(self.BRIEF) > 0.5

    def test_probe_non_logcat(self):
        assert logcat.probe('plain text') == 0.0

    def test_parse_threadtime_time(self):
        assert logcat.parse(self.THREADTIME)['time'] > 0

    def test_parse_debug_sev_6(self):
        assert logcat.parse(self.THREADTIME)['sev'] == 6

    def test_parse_error_sev_1(self):
        assert logcat.parse(self.WITH_YEAR)['sev'] == 1

    def test_parse_warn_sev_2(self):
        assert logcat.parse(self.WARN)['sev'] == 2

    def test_parse_threadtime_tag_in_msg(self):
        assert 'MyTag' in logcat.parse(self.THREADTIME)['msg']

    def test_parse_brief_tag_in_msg(self):
        assert 'MyTag' in logcat.parse(self.BRIEF)['msg']

    def test_parse_non_logcat_returns_empty(self):
        assert logcat.parse('plain text') == {}


# ===========================================================================
# gelf
# ===========================================================================

class TestGelf:

    def _line(self, **kw):
        import json as _json
        return _json.dumps(kw)

    def test_probe_short_message(self):
        assert gelf.probe(self._line(version='1.1', host='h', short_message='hi')) > 0.5

    def test_probe_full_message(self):
        assert gelf.probe(self._line(version='1.1', host='h', full_message='hi')) > 0.5

    def test_probe_version_host(self):
        assert gelf.probe(self._line(version='1.1', host='srv')) > 0.5

    def test_probe_non_gelf(self):
        assert gelf.probe('plain text') == 0.0

    def test_parse_message(self):
        r = gelf.parse(self._line(short_message='hello', version='1.1', host='srv'))
        assert 'hello' in r['msg']

    def test_parse_host_in_msg(self):
        r = gelf.parse(self._line(short_message='hello', host='myhost'))
        assert 'myhost' in r['msg']

    def test_parse_level_0_sev_1(self):
        r = gelf.parse(self._line(short_message='boom', level=0))
        assert r['sev'] == 1

    def test_parse_level_6_sev_6(self):
        r = gelf.parse(self._line(short_message='ok', level=6))
        assert r['sev'] == 6

    def test_parse_level_4_sev_2(self):
        r = gelf.parse(self._line(short_message='slow', level=4))
        assert r['sev'] == 2

    def test_parse_unix_timestamp(self):
        ts = time.time()
        r = gelf.parse(self._line(short_message='e', timestamp=ts))
        assert r['time'] == pytest.approx(ts, abs=1.0)

    def test_parse_non_gelf_returns_empty(self):
        assert gelf.parse('not json') == {}


# ===========================================================================
# cef
# ===========================================================================

class TestCef:

    LINE = 'CEF:0|Acme|Firewall|1.0|100|Intrusion Detected|7|src=10.0.0.1 dst=192.168.1.1'
    LOW  = 'CEF:0|Acme|IDS|1.0|42|Port Scan|2|src=10.0.0.2'
    SYSLOG = ('Jan 15 10:23:45 host syslogd: '
              'CEF:0|Acme|App|2.0|5|Login Failed|8|src=1.2.3.4 msg=bad password')

    def test_probe_valid(self):
        assert cef.probe(self.LINE) > 0.5

    def test_probe_syslog_prefix(self):
        assert cef.probe(self.SYSLOG) > 0.5

    def test_probe_non_cef(self):
        assert cef.probe('plain text') == 0.0

    def test_parse_high_severity_sev_1(self):
        assert cef.parse(self.LINE)['sev'] == 1

    def test_parse_low_severity_sev_5(self):
        assert cef.parse(self.LOW)['sev'] == 5

    def test_parse_msg_contains_name(self):
        assert 'Intrusion Detected' in cef.parse(self.LINE)['msg']

    def test_parse_msg_contains_src(self):
        assert '10.0.0.1' in cef.parse(self.LINE)['msg']

    def test_parse_msg_contains_vendor(self):
        assert 'Acme' in cef.parse(self.LINE)['msg']

    def test_parse_non_cef_returns_empty(self):
        assert cef.parse('plain text') == {}


# ===========================================================================
# mysql_error
# ===========================================================================

class TestMysqlError:

    ISO_NOTE = '2024-01-15T10:23:45.123456Z 0 [Note] ready for connections.'
    ISO_WARN = '2024-01-15T10:23:45.123456Z 0 [Warning] unsafe statement'
    ISO_ERR  = '2024-01-15T10:23:45.123456Z 1 [ERROR] can\'t open file'
    ISO_8    = '2024-01-15T10:23:45.123456Z 0 [System] [MY-010116] [Server] starting'
    OLD      = '240115 10:23:45 [Note] /usr/sbin/mysqld: ready for connections.'

    def test_probe_iso_note(self):
        assert mysql_error.probe(self.ISO_NOTE) > 0.5

    def test_probe_iso_8(self):
        assert mysql_error.probe(self.ISO_8) > 0.5

    def test_probe_old(self):
        assert mysql_error.probe(self.OLD) > 0.5

    def test_probe_non_mysql(self):
        assert mysql_error.probe('plain text') == 0.0

    def test_parse_note_sev_6(self):
        assert mysql_error.parse(self.ISO_NOTE)['sev'] == 6

    def test_parse_warning_sev_2(self):
        assert mysql_error.parse(self.ISO_WARN)['sev'] == 2

    def test_parse_error_sev_1(self):
        assert mysql_error.parse(self.ISO_ERR)['sev'] == 1

    def test_parse_iso_time(self):
        assert mysql_error.parse(self.ISO_NOTE)['time'] > 0

    def test_parse_old_time(self):
        assert mysql_error.parse(self.OLD)['time'] > 0

    def test_parse_msg(self):
        assert 'ready for connections' in mysql_error.parse(self.ISO_NOTE)['msg']

    def test_parse_non_mysql_returns_empty(self):
        assert mysql_error.parse('plain text') == {}


# ===========================================================================
# kubernetes
# ===========================================================================

class TestKubernetes:

    LINE    = '2024-01-15T10:23:45.123456789Z {"level":"info","msg":"server started"}'
    PLAIN   = '2024-01-15T10:23:45.123456789Z plain container output here'
    DOCKER  = '2024-01-15T10:23:45.123456789Z stdout F docker line'

    def test_probe_json_line(self):
        assert kubernetes.probe(self.LINE) > 0

    def test_probe_plain_line(self):
        assert kubernetes.probe(self.PLAIN) > 0

    def test_probe_docker_line_zero(self):
        # Docker format should not be claimed by k8s parser
        assert kubernetes.probe(self.DOCKER) == 0.0

    def test_probe_non_k8s(self):
        assert kubernetes.probe('plain text') == 0.0

    def test_parse_time(self):
        assert kubernetes.parse(self.LINE)['time'] > 0

    def test_parse_msg(self):
        assert kubernetes.parse(self.PLAIN)['msg'] == 'plain container output here'

    def test_parse_docker_line_returns_empty(self):
        assert kubernetes.parse(self.DOCKER) == {}

    def test_parse_non_k8s_returns_empty(self):
        assert kubernetes.parse('plain text') == {}


# ===========================================================================
# traefik
# ===========================================================================

class TestTraefik:

    JSON_LINE = json.dumps({
        'ClientAddr': '10.0.0.1:56789',
        'DownstreamStatus': 200,
        'Duration': 5_000_000,
        'RequestMethod': 'GET',
        'RequestPath': '/api/v1/users',
        'RouterName': 'my-router@docker',
        'ServiceName': 'my-svc@docker',
        'StartUTC': '2024-01-15T10:23:45.123456789Z',
        'level': 'info',
        'msg': '',
    })
    JSON_ERR = json.dumps({
        'ClientAddr': '10.0.0.1:56789',
        'DownstreamStatus': 503,
        'RequestMethod': 'POST',
        'RequestPath': '/api/submit',
        'RouterName': 'api@kubernetes',
        'StartUTC': '2024-01-15T10:23:45Z',
        'level': 'error',
        'msg': 'service unavailable',
    })
    TEXT_LINE = ('10.0.0.1 - - [15/Jan/2024:10:23:45 +0000] "GET /api HTTP/1.1" 200 512 '
                 '"-" "curl/7.68" 1 "my-router@docker" "http://backend:8080" 5ms')

    def test_probe_json(self):
        assert traefik.probe(self.JSON_LINE) > 0.5

    def test_probe_text(self):
        assert traefik.probe(self.TEXT_LINE) > 0.5

    def test_probe_non_traefik(self):
        assert traefik.probe('plain text') == 0.0

    def test_parse_json_time(self):
        assert traefik.parse(self.JSON_LINE)['time'] > 0

    def test_parse_json_200_sev_6(self):
        assert traefik.parse(self.JSON_LINE)['sev'] == 6

    def test_parse_json_503_sev_1(self):
        assert traefik.parse(self.JSON_ERR)['sev'] == 1

    def test_parse_json_msg_contains_path(self):
        assert '/api/v1/users' in traefik.parse(self.JSON_LINE)['msg']

    def test_parse_json_msg_contains_router(self):
        assert 'my-router@docker' in traefik.parse(self.JSON_LINE)['msg']

    def test_parse_text_time(self):
        assert traefik.parse(self.TEXT_LINE)['time'] > 0

    def test_parse_text_sev_6(self):
        assert traefik.parse(self.TEXT_LINE)['sev'] == 6

    def test_parse_non_traefik_returns_empty(self):
        assert traefik.parse('') == {}


# ===========================================================================
# csv_log
# ===========================================================================

class TestCsvLog:

    HEADER  = 'timestamp,level,message'
    DATA_OK = '2024-01-15T10:23:45,info,server started'
    DATA_ERR = '2024-01-15T10:23:45,error,connection failed'
    DATA_WARN = '2024-01-15T10:23:45,warning,disk almost full'

    NOHEADER_ROW = '2024-01-15T10:23:45,some event happened'

    def setup_method(self):
        csv_log._reset()

    def test_probe_header_line(self):
        assert csv_log.probe(self.HEADER) > 0.0

    def test_probe_data_with_iso_timestamp(self):
        assert csv_log.probe(self.DATA_OK) > 0.0

    def test_probe_single_field_zero(self):
        assert csv_log.probe('just one field') == 0.0

    def test_header_row_returns_empty(self):
        assert csv_log.parse(self.HEADER) == {}

    def test_parse_after_header_time(self):
        csv_log.parse(self.HEADER)
        r = csv_log.parse(self.DATA_OK)
        assert r['time'] > 0

    def test_parse_after_header_info_sev_6(self):
        csv_log.parse(self.HEADER)
        assert csv_log.parse(self.DATA_OK)['sev'] == 6

    def test_parse_after_header_error_sev_1(self):
        csv_log.parse(self.HEADER)
        assert csv_log.parse(self.DATA_ERR)['sev'] == 1

    def test_parse_after_header_warning_sev_2(self):
        csv_log.parse(self.HEADER)
        assert csv_log.parse(self.DATA_WARN)['sev'] == 2

    def test_parse_after_header_msg(self):
        csv_log.parse(self.HEADER)
        assert 'server started' in csv_log.parse(self.DATA_OK)['msg']

    def test_parse_without_header_detects_columns(self):
        r = csv_log.parse(self.NOHEADER_ROW)
        assert r['time'] > 0
        assert 'some event happened' in r['msg']

    def test_reset_clears_state(self):
        csv_log.parse(self.HEADER)
        csv_log.parse(self.DATA_OK)
        csv_log._reset()
        assert not csv_log._header_done
        assert csv_log._col_time is None
