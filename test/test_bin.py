"""Tests for the parsing and utility functions in bin/levv."""

import os
import time
import tempfile
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tempfile(content: bytes) -> str:
    """Write bytes to a named temp file and return its path."""
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    return path


# ---------------------------------------------------------------------------
# getVal
# ---------------------------------------------------------------------------

class TestGetVal:

    def test_dict_key_present(self, levv_bin):
        assert levv_bin.getVal({'a': 42}, 'a') == 42

    def test_dict_key_missing_returns_default(self, levv_bin):
        assert levv_bin.getVal({}, 'x') == 0

    def test_dict_key_missing_custom_default(self, levv_bin):
        assert levv_bin.getVal({}, 'x', 99) == 99

    def test_list_index_in_range(self, levv_bin):
        assert levv_bin.getVal([10, 20, 30], 1) == 20

    def test_list_index_out_of_range_returns_default(self, levv_bin):
        assert levv_bin.getVal([10, 20], 5) == 0

    def test_list_index_out_of_range_custom_default(self, levv_bin):
        assert levv_bin.getVal([], 0, 'fallback') == 'fallback'


# ---------------------------------------------------------------------------
# makeDisplayPath
# ---------------------------------------------------------------------------

class TestMakeDisplayPath:

    def test_short_path_returned_unchanged(self, levv_bin):
        assert levv_bin.makeDisplayPath('/a/b/c', 100) == '/a/b/c'

    def test_path_at_exact_limit_unchanged(self, levv_bin):
        path = '/a/b/c'
        assert levv_bin.makeDisplayPath(path, len(path)) == path

    def test_long_path_fits_within_limit(self, levv_bin):
        result = levv_bin.makeDisplayPath('/very/long/path/to/some/file.log', 20)
        assert len(result) <= 20

    def test_long_path_contains_ellipsis(self, levv_bin):
        result = levv_bin.makeDisplayPath('/very/long/path/to/some/file.log', 20)
        assert '...' in result

    def test_long_path_preserves_filename(self, levv_bin):
        result = levv_bin.makeDisplayPath('/very/long/path/to/some/file.log', 20)
        assert 'file.log' in result

    def test_custom_separator(self, levv_bin):
        result = levv_bin.makeDisplayPath('a.b.c.d.e.f', 8, sep='.')
        assert len(result) <= 8


# ---------------------------------------------------------------------------
# findDate
# ---------------------------------------------------------------------------

class TestFindDate:

    def test_iso_datetime_found(self, levv_bin):
        length, date = levv_bin.findDate('2023-06-15 12:00:00 some message')
        assert length > 0
        assert date is not None and date != 0

    def test_iso_datetime_position_advances_into_message(self, levv_bin):
        text = '2023-06-15 12:00:00 some message'
        length, date = levv_bin.findDate(text)
        # findDate finds the longest stable date prefix; the message text
        # must appear somewhere after that cut point.
        assert 'some message' in text[length:]

    def test_no_date_returns_zero(self, levv_bin):
        length, date = levv_bin.findDate('no date here whatsoever')
        assert length == 0
        assert date == 0

    def test_short_text_no_date(self, levv_bin):
        length, date = levv_bin.findDate('hello')
        assert length == 0

    def test_empty_string(self, levv_bin):
        length, date = levv_bin.findDate('')
        assert length == 0


# ---------------------------------------------------------------------------
# processLineKMsg
# ---------------------------------------------------------------------------

class TestProcessLineKMsg:

    # Kernel message format:  sev,seq,offset_usecs,flags;message
    VALID = '6,339,5085350,-;NET: Registered PF_ALG protocol family'

    def test_valid_line_has_required_keys(self, levv_bin):
        r = levv_bin.processLineKMsg(self.VALID)
        assert 'sev' in r and 'seq' in r and 'time' in r and 'msg' in r

    def test_sev_extracted(self, levv_bin):
        r = levv_bin.processLineKMsg(self.VALID)
        assert r['sev'] == '6'

    def test_seq_extracted(self, levv_bin):
        r = levv_bin.processLineKMsg(self.VALID)
        assert r['seq'] == '339'

    def test_time_is_positive_float(self, levv_bin):
        r = levv_bin.processLineKMsg(self.VALID)
        assert isinstance(r['time'], float)
        assert r['time'] > 0

    def test_time_offset_added_to_boot(self, levv_bin):
        import psutil
        offset_sec = 5085350 / 1_000_000.0  # from the test line
        boot = float(psutil.boot_time()) or time.time()
        r = levv_bin.processLineKMsg(self.VALID)
        assert r['time'] == pytest.approx(offset_sec + boot, abs=1.0)

    def test_msg_extracted(self, levv_bin):
        r = levv_bin.processLineKMsg(self.VALID)
        assert r['msg'].endswith('NET: Registered PF_ALG protocol family')

    def test_too_few_fields_returns_empty(self, levv_bin):
        assert levv_bin.processLineKMsg('6,339') == {}

    def test_three_fields_returns_empty(self, levv_bin):
        assert levv_bin.processLineKMsg('6,339,5085350') == {}


# ---------------------------------------------------------------------------
# processLineWww
# ---------------------------------------------------------------------------

class TestProcessLineWww:

    def _line(self, status, path='/', sz='1024'):
        return (f'127.0.0.1 - - [01/Jan/2024:00:00:00 +0000]'
                f' "GET {path} HTTP/1.1" {status} {sz}')

    def test_http_200_sev_6(self, levv_bin):
        r = levv_bin.processLineWww(self._line(200))
        assert r['sev'] == 6

    def test_http_404_sev_2(self, levv_bin):
        r = levv_bin.processLineWww(self._line(404))
        assert r['sev'] == 2

    def test_http_500_sev_1(self, levv_bin):
        r = levv_bin.processLineWww(self._line(500))
        assert r['sev'] == 1

    def test_http_301_sev_3(self, levv_bin):
        r = levv_bin.processLineWww(self._line(301))
        assert r['sev'] == 3

    def test_result_contains_ip(self, levv_bin):
        r = levv_bin.processLineWww(self._line(200))
        assert '127.0.0.1' in r['msg']

    def test_result_contains_status_code(self, levv_bin):
        r = levv_bin.processLineWww(self._line(200))
        assert '200' in r['msg']

    def test_result_contains_size(self, levv_bin):
        r = levv_bin.processLineWww(self._line(200, sz='9999'))
        assert '9999' in r['msg']

    def test_time_is_float(self, levv_bin):
        r = levv_bin.processLineWww(self._line(200))
        assert isinstance(r['time'], float)

    def test_too_short_line_returns_empty(self, levv_bin):
        assert levv_bin.processLineWww('127.0.0.1 - -') == {}


# ---------------------------------------------------------------------------
# processLineDate
# ---------------------------------------------------------------------------

class TestProcessLineDate:

    def test_iso_date_at_start(self, levv_bin):
        r = levv_bin.processLineDate('2023-06-15 12:00:00 server started')
        assert 'time' in r
        assert isinstance(r['time'], float)

    def test_message_extracted(self, levv_bin):
        r = levv_bin.processLineDate('2023-06-15 12:00:00 server started')
        assert 'server started' in r['msg']

    def test_severity_computed_from_message(self, levv_bin):
        r = levv_bin.processLineDate('2023-06-15 12:00:00 error detected')
        assert r['sev'] == 1

    def test_no_date_returns_empty(self, levv_bin):
        r = levv_bin.processLineDate('no date in this line at all')
        assert r == {}

    def test_empty_string_returns_empty(self, levv_bin):
        r = levv_bin.processLineDate('')
        assert r == {}


# ---------------------------------------------------------------------------
# processLineAuto
# ---------------------------------------------------------------------------

class TestProcessLineAuto:

    def test_unix_timestamp_parsed(self, levv_bin):
        ts = time.time() - 60   # within 1-year window used by processLineAuto
        r = levv_bin.processLineAuto(f'{ts} test message')
        assert r['time'] == pytest.approx(ts, abs=1.0)

    def test_unix_timestamp_message_extracted(self, levv_bin):
        ts = time.time() - 60
        r = levv_bin.processLineAuto(f'{ts} test message')
        assert r['msg'] == 'test message'

    def test_unix_timestamp_with_priority(self, levv_bin):
        ts = time.time() - 60
        r = levv_bin.processLineAuto(f'{ts} 3 some message')
        assert r['time'] == pytest.approx(ts, abs=1.0)
        assert r['sev'] == 3
        assert r['msg'] == 'some message'

    def test_date_string_fallback(self, levv_bin):
        r = levv_bin.processLineAuto('2023-06-15 12:00:00 server started')
        assert 'time' in r
        assert isinstance(r['time'], float)

    def test_plain_text_uses_current_time(self, levv_bin):
        before = time.time()
        r = levv_bin.processLineAuto('completely plain log line')
        after = time.time()
        assert before <= r['time'] <= after

    def test_plain_text_message_preserved(self, levv_bin):
        r = levv_bin.processLineAuto('completely plain log line')
        assert r['msg'] == 'completely plain log line'

    def test_empty_string_returns_empty(self, levv_bin):
        r = levv_bin.processLineAuto('')
        assert r == {}

    def test_out_of_range_timestamp_not_used(self, levv_bin):
        # A timestamp far in the past falls outside the ±1-year window
        r = levv_bin.processLineAuto('1000000 message with old timestamp')
        # Time should not be 1000000; it falls back to current time or date parse
        assert r['time'] != pytest.approx(1000000, abs=1.0)


# ---------------------------------------------------------------------------
# processLine — dispatch and regression tests
# ---------------------------------------------------------------------------

class TestProcessLine:

    def test_text_format_uses_current_time(self, levv_bin):
        before = time.time()
        r = levv_bin.processLine({'inputformat': 'text'}, 'hello world')
        after = time.time()
        assert before <= r['time'] <= after
        assert r['msg'] == 'hello world'

    def test_date_format_does_not_raise(self, levv_bin):
        """Regression: was calling undefined processDate(); now calls processLineDate()."""
        r = levv_bin.processLine({'inputformat': 'date'}, '2023-06-15 12:00:00 an event')
        assert isinstance(r, dict)

    def test_date_format_returns_time(self, levv_bin):
        r = levv_bin.processLine({'inputformat': 'date'}, '2023-06-15 12:00:00 an event')
        assert 'time' in r

    def test_kmsg_format(self, levv_bin):
        r = levv_bin.processLine({'inputformat': 'kmsg'},
                                 '6,339,5085350,-;kernel message')
        assert 'sev' in r and 'time' in r and 'msg' in r

    def test_www_format_http_200(self, levv_bin):
        line = ('127.0.0.1 - - [01/Jan/2024:00:00:00 +0000]'
                ' "GET / HTTP/1.1" 200 512')
        r = levv_bin.processLine({'inputformat': 'www'}, line)
        assert r['sev'] == 6

    def test_auto_format_timestamp(self, levv_bin):
        ts = time.time() - 60
        r = levv_bin.processLine({'inputformat': 'auto'}, f'{ts} event')
        assert r['time'] == pytest.approx(ts, abs=1.0)

    def test_unknown_format_falls_back_to_auto(self, levv_bin):
        ts = time.time() - 60
        r = levv_bin.processLine({'inputformat': 'nonexistent'}, f'{ts} event')
        assert r['time'] == pytest.approx(ts, abs=1.0)


# ---------------------------------------------------------------------------
# setFilePtr
# ---------------------------------------------------------------------------

class TestSetFilePtr:

    def test_seek_from_end(self, levv_bin):
        """Common usage: negative offset seeks from end of file."""
        path = make_tempfile(b'0123456789')
        try:
            with open(path, 'rb') as fh:
                levv_bin.setFilePtr(fh, -4)
                assert fh.read() == b'6789'
        finally:
            os.unlink(path)

    def test_seek_from_end_larger_than_file_seeks_to_start(self, levv_bin):
        path = make_tempfile(b'hello')
        try:
            with open(path, 'rb') as fh:
                levv_bin.setFilePtr(fh, -1000)
                assert fh.read() == b'hello'
        finally:
            os.unlink(path)

    def test_seek_from_start(self, levv_bin):
        """Regression: was using os.SEEK_BEGIN (AttributeError); now os.SEEK_SET."""
        path = make_tempfile(b'0123456789')
        try:
            with open(path, 'rb') as fh:
                levv_bin.setFilePtr(fh, 3)
                assert fh.read() == b'3456789'
        finally:
            os.unlink(path)

    def test_seek_from_start_larger_than_file_clamps(self, levv_bin):
        path = make_tempfile(b'hello')
        try:
            with open(path, 'rb') as fh:
                levv_bin.setFilePtr(fh, 1000)
                assert fh.read() == b''
        finally:
            os.unlink(path)

    def test_empty_file_returns_zero(self, levv_bin):
        path = make_tempfile(b'')
        try:
            with open(path, 'rb') as fh:
                result = levv_bin.setFilePtr(fh, -100)
            assert result == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# getLine
# ---------------------------------------------------------------------------

class TestGetLine:

    def _reset(self, levv_bin):
        levv_bin.inbuf = ''

    def test_reads_single_line(self, levv_bin):
        self._reset(levv_bin)
        path = make_tempfile(b'hello world\n')
        try:
            with open(path, 'rb') as fh:
                line = levv_bin.getLine(fh)
            assert line == 'hello world'  # \n stripped as control char
        finally:
            os.unlink(path)

    def test_reads_multiple_lines_sequentially(self, levv_bin):
        self._reset(levv_bin)
        path = make_tempfile(b'line one\nline two\n')
        try:
            with open(path, 'rb') as fh:
                l1 = levv_bin.getLine(fh)
                l2 = levv_bin.getLine(fh)
            assert l1 == 'line one'
            assert l2 == 'line two'
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty_string(self, levv_bin):
        self._reset(levv_bin)
        path = make_tempfile(b'')
        try:
            with open(path, 'rb') as fh:
                line = levv_bin.getLine(fh)
            assert line == ''
        finally:
            os.unlink(path)

    def test_control_characters_stripped(self, levv_bin):
        self._reset(levv_bin)
        path = make_tempfile(b'hello\x01\x02world\n')
        try:
            with open(path, 'rb') as fh:
                line = levv_bin.getLine(fh)
            assert '\x01' not in line and '\x02' not in line
            assert 'hello' in line and 'world' in line
        finally:
            os.unlink(path)

    def test_custom_separator_splits_record(self, levv_bin):
        self._reset(levv_bin)
        path = make_tempfile(b'part1---part2---part3\n')
        try:
            with open(path, 'rb') as fh:
                p1 = levv_bin.getLine(fh, '---')
                p2 = levv_bin.getLine(fh, '---')
            assert p1 == 'part1'
            assert p2 == 'part2'
        finally:
            os.unlink(path)

    def test_custom_separator_exhausted_returns_empty(self, levv_bin):
        self._reset(levv_bin)
        path = make_tempfile(b'only one record\n')
        try:
            with open(path, 'rb') as fh:
                levv_bin.getLine(fh, '---')   # no separator in content; drains file
                extra = levv_bin.getLine(fh, '---')  # EOF — must not infinite-loop
            assert extra == ''
        finally:
            os.unlink(path)
