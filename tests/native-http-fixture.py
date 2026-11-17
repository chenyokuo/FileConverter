"""Owned live HLS fixture for native package QA; no engine/job mocks."""
import json,sys
from test_p3 import P3Tests
P3Tests.setUpClass()
try:
 print(json.dumps({'url':P3Tests.base+'master.m3u8'}),flush=True)
 sys.stdin.readline()
finally:P3Tests.tearDownClass()
