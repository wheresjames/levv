"""Tests for the utility functions that remain in bin/levv."""

import os
import time
import tempfile
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tempfile(content: bytes) -> str:
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
# processLine — dispatch through levv.parse_line
# ---------------------------------------------------------------------------

class TestProcessLine:

    def test_text_format_uses_current_time(self, levv_bin):
        before = time.time()
        r = levv_bin.processLine({'inputformat': 'text'}, 'hello world')
        after = time.time()
        assert before <= r['time'] <= after
        assert r['msg'] == 'hello world'

    def test_date_format_does_not_raise(self, levv_bin):
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
            assert line == 'hello world'
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
                levv_bin.getLine(fh, '---')
                extra = levv_bin.getLine(fh, '---')
            assert extra == ''
        finally:
            os.unlink(path)
