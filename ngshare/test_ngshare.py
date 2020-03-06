'''
    Tests for ngshare APIs
'''

import sys
import json
import base64
import datetime
import hashlib
import requests

# pylint: disable=comparison-with-callable
# pylint: disable=global-statement
# pylint: disable=invalid-name
# pylint: disable=len-as-condition

URL_PREFIX = 'http://127.0.0.1:12121'
GET = requests.get
POST = requests.post
user = None

def request_page(url, data=None, params=None, method=GET):
    'Request a page'
    assert url.startswith('/') and not url.startswith('//')
    resp = method(URL_PREFIX + url, data=data, params=params)
    return resp.json()

def assert_success(url, data=None, params=None, method=GET):
    'Assert requesting a page is success'
    global user
    if user is not None:
        if method == GET:
            params = params if params is not None else {}
            params['user'] = user
        else:
            data = data if data is not None else {}
            data['user'] = user
    resp = request_page(url, data, params, method)
    if not resp['success']:
        print(repr(resp), file=sys.stderr)
        raise Exception('Not success')
    return resp

def assert_fail(url, data=None, params=None, method=GET, msg=None):
    'Assert requesting a page is failing (with matching message)'
    global user
    if user is not None:
        if method == GET:
            params = params if params is not None else {}
            params['user'] = user
        else:
            data = data if data is not None else {}
            data['user'] = user
    resp = request_page(url, data, params, method)
    if resp['success']:
        print(repr(resp), file=sys.stderr)
        raise Exception('Success')
    if msg is not None:
        assert resp['message'] == msg
    return resp

def test_init():
    'Clear database'
    global user
    user = 'none'
    assert assert_success('/api/initialize-Data6ase')['message'] == 'done'

def test_list_courses():
    'Test GET /api/courses'
    url = '/api/courses'
    global user
    user = 'kevin'
    assert assert_success(url)['courses'] == ['course1']
    user = 'abigail'
    assert assert_success(url)['courses'] == ['course2']
    user = 'lawrence'
    assert assert_success(url)['courses'] == ['course1']
    user = 'eric'
    assert assert_success(url)['courses'] == ['course2']

def test_add_courses():
    'Test GET /api/course/<course_id>'
    url = '/api/course/'
    global user
    user = 'eric'
    assert_success(url + 'course3', method=POST)
    assert_fail(url + 'course3', method=POST, msg='Course already exists')
    assert assert_success('/api/courses')['courses'] == ['course2', 'course3']

def test_list_assignments():
    'Test GET /api/assignments/<course_id>'
    url = '/api/assignments/'
    global user
    user = 'kevin'
    assert_fail(url + 'course2',
                msg='Permission denied (not related to course)')
    user = 'abigail'
    assert assert_success(url + 'course2')['assignments'] == \
            ['assignment2a', 'assignment2b']
    user = 'lawrence'
    assert_fail(url + 'course2',
                msg='Permission denied (not related to course)')
    user = 'eric'
    assert assert_success(url + 'course2')['assignments'] == \
            ['assignment2a', 'assignment2b']
    assert_fail(url + 'jkl', msg='Course not found')

def test_download_assignment():
    'Test GET /api/assignment/<course_id>/<assignment_id>'
    url = '/api/assignment/'
    global user
    user = 'kevin'
    files = assert_success(url + 'course1/challenge')['files']
    assert files[0]['path'] == 'file2'
    assert base64.b64decode(files[0]['content'].encode()) == b'22222'
    assert files[0]['checksum'] == hashlib.md5(b'22222').hexdigest()
    assert_fail(url + 'jkl/challenger', msg='Course not found')
    assert_fail(url + 'course1/challenger', msg='Assignment not found')
    # Check list_only
    files = assert_success(url + 'course1/challenge?list_only=true')['files']
    assert set(files[0]) == {'path', 'checksum'}
    assert files[0]['path'] == 'file2'
    assert files[0]['checksum'] == hashlib.md5(b'22222').hexdigest()
    user = 'eric'
    assert_fail(url + 'course1/challenge',
                msg='Permission denied (not related to course)')

def test_release_assignment():
    'Test POST /api/assignment/<course_id>/<assignment_id>'
    url = '/api/assignment/'
    global user
    data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
                                 {'path': 'b', 'content': 'amtsCg=='}])}
    user = 'kevin'
    assert_fail(url + 'jkl/challenger', method=POST,
                data=data, msg='Course not found')
    assert_fail(url + 'course1/challenger', method=POST,
                msg='Please supply files')
    assert_success(url + 'course1/challenger', method=POST,
                   data=data)
    assert_fail(url + 'course1/challenger', method=POST,
                data=data, msg='Assignment already exists')
    data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg'}])
    assert_fail(url + 'course1/challenges', method=POST,
                data=data, msg='Content cannot be base64 decoded')
    for pathname in ['/a', '/', '', '../etc', 'a/./a.py', 'a/.']:
        data['files'] = json.dumps([{'path': pathname, 'content': ''}])
        assert_fail(url + 'course1/challenges', method=POST,
                    data=data, msg='Illegal path')
    user = 'abigail'
    assert_fail(url + 'course1/challenger', method=POST,
                data=data, msg='Permission denied (not course instructor)')
    user = 'lawrence'
    assert_fail(url + 'course1/challenger', method=POST,
                data=data, msg='Permission denied (not course instructor)')
    user = 'eric'
    assert_fail(url + 'course1/challenger', method=POST,
                data=data, msg='Permission denied (not course instructor)')

def test_list_submissions():
    'Test GET /api/submissions/<course_id>/<assignment_id>'
    url = '/api/submissions/'
    global user
    user = 'kevin'
    assert_fail(url + 'jkl/challenge', msg='Course not found')
    assert_fail(url + 'course1/challenges',
                msg='Assignment not found')
    result = assert_success(url + 'course1/challenge')
    assert len(result['submissions']) == 2
    assert set(result['submissions'][0]) == {'student_id', 'timestamp'}
    assert result['submissions'][0]['student_id'] == 'lawrence'
    assert result['submissions'][1]['student_id'] == 'lawrence'
    user = 'abigail'
    result = assert_success(url + 'course2/assignment2a')
    assert len(result['submissions']) == 0
    user = 'eric'
    assert_fail(url + 'course1/challenges',
                msg='Permission denied (not course instructor)')
    assert_fail(url + 'course2/assignment2a',
                msg='Permission denied (not course instructor)')

def test_list_student_submission():
    'Test GET /api/submissions/<course_id>/<assignment_id>/<student_id>'
    url = '/api/submissions/'
    global user
    user = 'kevin'
    assert_fail(url + 'jkl/challenge/st', msg='Course not found')
    assert_fail(url + 'course1/challenges/st', msg='Assignment not found')
    assert_fail(url + 'course1/challenge/st', msg='Student not found')
    result = assert_success(url + 'course1/challenge/lawrence')
    assert len(result['submissions']) == 2
    assert set(result['submissions'][0]) == {'student_id', 'timestamp'}
    user = 'eric'
    result = assert_success(url + 'course2/assignment2a/eric')
    assert len(result['submissions']) == 0
    user = 'kevin'
    assert_fail(url + 'course2/assignment2a/eric',
                msg='Permission denied (not course instructor)')
    user = 'abigail'
    assert_fail(url + 'course1/challenge/lawrence',
                msg='Permission denied (not course instructor)')
    user = 'lawrence'
    assert_success(url + 'course1/challenge/lawrence')
    user = 'eric'
    assert_fail(url + 'course1/challenge/lawrence',
                msg='Permission denied (not course instructor)')

def test_submit_assignment():
    'Test POST /api/submission/<course_id>/<assignment_id>'
    url = '/api/submission/'
    global user
    user = 'kevin'
    data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
                                 {'path': 'b', 'content': 'amtsCg=='}])}
    assert_fail(url + 'jkl/challenge', method=POST,
                msg='Course not found')
    assert_fail(url + 'course1/challenges', method=POST,
                msg='Assignment not found')
    user = 'lawrence'
    assert_fail(url + 'course1/challenge', method=POST,
                msg='Please supply files')
    assert_success(url + 'course1/challenge', method=POST, data=data)
    data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg=='}])
    assert_success(url + 'course1/challenge', method=POST, data=data)
    data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg'}])
    assert_fail(url + 'course1/challenge', method=POST,
                data=data, msg='Content cannot be base64 decoded')
    user = 'kevin'
    result = assert_success('/api/submissions/course1/challenge')
    assert len(result['submissions']) == 4    # 2 from init, 2 from this
    user = 'eric'
    assert_fail(url + 'course1/challenge', method=POST,
                msg='Permission denied (not related to course)')

def test_download_submission():
    'Test GET /api/submission/<course_id>/<assignment_id>/<student_id>'
    url = '/api/submission/'
    global user
    user = 'kevin'
    assert_fail(url + 'jkl/challenge/st', msg='Course not found')
    assert_fail(url + 'course1/challenges/st', msg='Assignment not found')
    assert_fail(url + 'course1/challenge/st', msg='Student not found')
    # Test get latest
    result = assert_success(url + 'course1/challenge/lawrence')
    files = result['files']
    assert len(files) == 1
    file_obj = next(filter(lambda x: x['path'] == 'a', files))
    assert base64.b64decode(file_obj['content'].encode()) == b'jkl\n'
    assert file_obj['checksum'] == hashlib.md5(b'jkl\n').hexdigest()
    user = 'abigail'
    assert_fail(url + 'course2/assignment2a/eric', msg='Submission not found')
    # Test get latest with list_only
    user = 'kevin'
    result = assert_success(url + 'course1/challenge/lawrence',
                            params={'list_only': 'true'})
    files = result['files']
    assert len(files) == 1
    assert set(files[0]) == {'path', 'checksum'}
    assert files[0]['path'] == 'a'
    assert files[0]['checksum'] == hashlib.md5(b'jkl\n').hexdigest()
    # Test timestamp
    result = assert_success('/api/submissions/course1/challenge/lawrence')
    timestamp = sorted(map(lambda x: x['timestamp'], result['submissions']))[0]
    result = assert_success(url + 'course1/challenge/lawrence',
                            {'timestamp': timestamp})
    files = result['files']
    assert len(files) == 1
    file_obj = next(filter(lambda x: x['path'] == 'file3', files))
    assert base64.b64decode(file_obj['content'].encode()) == b'33333'
    assert file_obj['checksum'] == hashlib.md5(b'33333').hexdigest()
    # Test timestamp with list_only
    result = assert_success('/api/submissions/course1/challenge/lawrence')
    timestamp = sorted(map(lambda x: x['timestamp'], result['submissions']))[0]
    result = assert_success(url + 'course1/challenge/lawrence',
                            {'timestamp': timestamp, 'list_only': 'true'})
    files = result['files']
    assert len(files) == 1
    file_obj = next(filter(lambda x: x['path'] == 'file3', files))
    assert 'content' not in file_obj
    assert file_obj['checksum'] == hashlib.md5(b'33333').hexdigest()
    # Test timestamp not found
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f %Z')
    assert_fail(url + 'course1/challenge/lawrence', {'timestamp': timestamp},
                msg='Submission not found')
    # Test permission
    user = 'eric'
    assert_fail(url + 'course2/assignment2a/eric',
                msg='Permission denied (not course instructor)')

def test_upload_feedback():
    'Test POST /api/feedback/<course_id>/<assignment_id>/<student_id>'
    url = '/api/feedback/'
    global user
    user = 'kevin'
    data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
                                 {'path': 'b', 'content': 'amtsCg=='}]),
            'timestamp': '2020-01-01 00:00:00.000000 '}
    assert_fail(url + 'jkl/challenge/st', method=POST, data=data,
                msg='Course not found')
    assert_fail(url + 'course1/challenges/st', method=POST, data=data,
                msg='Assignment not found')
    assert_fail(url + 'course1/challenge/st', method=POST, data=data,
                msg='Student not found')
    assert_success(url + 'course1/challenge/lawrence', method=POST, data=data)
    data['files'] = json.dumps([{'path': 'c', 'content': 'amtsCf=='}])
    assert_success(url + 'course1/challenge/lawrence', method=POST, data=data)
    assert_fail(url + 'course1/challenge/lawrence', method=POST, data={},
                msg='Please supply timestamp')
    assert_fail(url + 'course1/challenge/lawrence', method=POST,
                data={'timestamp': 'a'}, msg='Time format incorrect')
    user = 'abigail'
    assert_fail(url + 'course2/assignment2a/eric', method=POST, data=data,
                msg='Submission not found')
    assert_fail(url + 'course2/assignment2a/eric', method=POST,
                data={'timestamp': data['timestamp']},
                msg='Submission not found')
    user = 'eric'
    assert_fail(url + 'course2/assignment2a/eric', method=POST, data=data,
                msg='Permission denied (not course instructor)')

def test_download_feedback():
    'Test GET /api/feedback/<course_id>/<assignment_id>/<student_id>'
    url = '/api/feedback/'
    global user
    user = 'kevin'
    assert_fail(url + 'jkl/challenge/st', msg='Course not found')
    assert_fail(url + 'course1/challenges/st', msg='Assignment not found')
    assert_fail(url + 'course1/challenge/st', msg='Student not found')
    meta = assert_success('/api/submission/course1/challenge/lawrence')
    timestamp = meta['timestamp']
    assert_fail(url + 'course1/challenge/lawrence', params={},
                msg='Please supply timestamp')
    assert_fail(url + 'course1/challenge/lawrence', params={'timestamp': 'a'},
                msg='Time format incorrect')
    user = 'eric'
    assert_fail(url + 'course2/assignment2a/eric',
                params={'timestamp': timestamp}, msg='Submission not found')
    user = 'kevin'
    feedback = assert_success(url + 'course1/challenge/lawrence',
                              params={'timestamp': timestamp})
    assert feedback['files'] == []
    # Submit again ('amtsDg==' is 'jkl\x0e')
    data = {'files': json.dumps([{'path': 'a', 'content': 'amtsDg=='}]),
            'timestamp': timestamp}
    assert_success(url + 'course1/challenge/lawrence', method=POST, data=data)
    # Fetch again
    feedback = assert_success(url + 'course1/challenge/lawrence',
                              params={'timestamp': timestamp})
    assert len(feedback['files']) == 1
    assert feedback['files'][0]['path'] == 'a'
    file_obj = feedback['files'][0]
    assert base64.b64decode(file_obj['content'].encode()) == b'jkl\x0e'
    assert file_obj['checksum'] == hashlib.md5(b'jkl\x0e').hexdigest()
    # Again, submit again ('nmtsDg==' is 'nkl\x0e')
    data = {'files': json.dumps([{'path': 'a', 'content': 'bmtsDg=='}]),
            'timestamp': timestamp}
    assert_success(url + 'course1/challenge/lawrence', method=POST, data=data)
    # Again, fetch again
    feedback = assert_success(url + 'course1/challenge/lawrence',
                              params={'timestamp': timestamp})
    assert len(feedback['files']) == 1
    file_obj = feedback['files'][0]
    assert file_obj['path'] == 'a'
    assert base64.b64decode(file_obj['content'].encode()) == b'nkl\x0e'
    assert file_obj['checksum'] == hashlib.md5(b'nkl\x0e').hexdigest()
    # Check list_only
    feedback = assert_success(url + 'course1/challenge/lawrence',
                              params={'timestamp': timestamp,
                                      'list_only': 'true'})
    assert len(feedback['files']) == 1
    assert set(feedback['files'][0]) == {'path', 'checksum'}
    assert file_obj['checksum'] == hashlib.md5(b'nkl\x0e').hexdigest()
    assert feedback['files'][0]['path'] == 'a'
    # Permission check
    user = 'kevin'
    assert_fail(url + 'course1/challenge/lawrence',
                msg='Please supply timestamp')
    user = 'abigail'
    assert_fail(url + 'course1/challenge/lawrence',
                msg='Permission denied (not course instructor)')
    user = 'lawrence'
    assert_fail(url + 'course1/challenge/lawrence',
                msg='Please supply timestamp')
    user = 'eric'
    assert_fail(url + 'course1/challenge/lawrence',
                msg='Permission denied (not course instructor)')
