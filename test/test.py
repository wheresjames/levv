#!/usr/bin/env python3

import json
import levv
Log = print

try:
    import sparen
    Log = sparen.log
except Exception as e:
    Log = print


def test_1():

    Log("Test 1")

    # Test regex group names

    # time:
    t1 = '21-12-07 21:01:24: [ERR] Exception!'
    r, s = levv.filterLine(levv.getLogTemplate('time:'), t1)
    Log(r)
    assert r['time'] == 1198299684
    assert r['msg'] == '[ERR] Exception!'

    # pm2
    t1 = '1|appname | 21-12-07 21:01:24: [ERR] Exception!'
    r, s = levv.filterLine(levv.getLogTemplate('pm2'), t1)
    Log(r)
    assert r['sev'] == 1
    assert r['time'] == 1198299684
    assert r['msg'] == '[ERR] Exception!'



def main():

    Log(json.dumps(levv.__info__, indent=2))

    test_1()



if __name__ == '__main__':
    main()
