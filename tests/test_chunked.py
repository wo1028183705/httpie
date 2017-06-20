from utils import http, HTTP_OK, TESTS_ROOT


def test_chunked_no_data(httpbin):
    r = http('POST', httpbin + '/post', '--chunked')
    assert HTTP_OK in r
    assert r.json['headers']['Transfer-Encoding'] == 'Chunked'
