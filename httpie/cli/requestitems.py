import os
from io import BytesIO

from httpie.cli.constants import (
    SEP_HEADERS, SEP_HEADERS_EMPTY, SEP_DATA, SEP_DATA_RAW_JSON, SEP_FILES,
    SEP_DATA_EMBED_FILE, SEP_DATA_EMBED_RAW_JSON_FILE, SEP_QUERY,
)
from httpie.cli.dicts import (
    RequestHeadersDict, RequestJSONDataDict, RequestQueryParamsDict,
    RequestDataDict, RequestFilesDict,
)
from httpie.cli.exceptions import ParseError
from httpie.utils import (
    load_json_preserve_order, get_content_type,
)


def parse_items(items, as_form=False, chunked=False):
    request_items = RequestItems(as_form=as_form, chunked=chunked)
    request_items.parse(items)
    return request_items


class RequestItems:

    def __init__(self, as_form=False, chunked=False):
        self.headers = RequestHeadersDict()
        self.data = RequestDataDict() if as_form else RequestJSONDataDict()
        self.files = RequestFilesDict()
        self.params = RequestQueryParamsDict()
        self.chunked = chunked

    def parse(self, items):
        parse_file_item = (
            self.parse_file_item
            if not self.chunked else
            self.parse_file_item_chunked
        )
        parse_file_item = self.parse_file_item_chunked
        rules = {
            SEP_HEADERS: (self.headers, self.parse_header_item),
            SEP_HEADERS_EMPTY: (self.headers, self.parse_empty_header_item),
            SEP_QUERY: (self.params, self.parse_query_param_item),
            SEP_FILES: (self.files, parse_file_item),
            SEP_DATA: (self.data, self.parse_data_item),
            SEP_DATA_EMBED_FILE: (self.data, self.parse_data_embed_text_file),
            SEP_DATA_EMBED_RAW_JSON_FILE: (self.data, self.parse_data_embed_raw_json_file),
            SEP_DATA_RAW_JSON: (self.data, self.parse_data_raw_json_embed_item),
        }
        for item in items:
            target, parser = rules[item.sep]
            target[item.key] = parser(item)

    def _load_text_file(self, item):
        path = item.value
        try:
            with open(os.path.expanduser(path), 'rb') as f:
                return f.read().decode('utf8')
        except IOError as e:
            raise ParseError('"%s": %s' % (item.orig, e))
        except UnicodeDecodeError:
            raise ParseError(
                '"%s": cannot embed the content of "%s",'
                ' not a UTF8 or ASCII-encoded text file'
                % (item.orig, item.value)
            )

    def _load_json(self, item, contents):
        try:
            return load_json_preserve_order(contents)
        except ValueError as e:
            raise ParseError('"%s": %s' % (item.orig, e))

    def parse_header_item(self, item):
        return item.value or None

    def parse_empty_header_item(self, item):
        if item.value:
            raise ParseError(
                'Invalid item "%s" '
                '(to specify an empty header use `Header;`)'
                % item.orig
            )
        return item.value

    def parse_query_param_item(self, item):
        return item.value

    def parse_file_item(self, item):
        fn = item.value
        try:
            with open(os.path.expanduser(fn), 'rb') as f:
                contents = f.read()
        except IOError as e:
            raise ParseError('"%s": %s' % (item.orig, e))
        return os.path.basename(fn), BytesIO(contents), get_content_type(fn)

    def parse_file_item_chunked(self, item):
        fn = item.value
        try:
            f = open(os.path.expanduser(fn), 'rb')
        except IOError as e:
            raise ParseError('"%s": %s' % (item.orig, e))
        return os.path.basename(fn), f, get_content_type(fn)

    def parse_data_item(self, item):
        return item.value

    def parse_data_embed_text_file(self, item):
        return self._load_text_file(item)

    def parse_data_embed_raw_json_file(self, item):
        contents = self._load_text_file(item)
        value = self._load_json(item, contents)
        return value

    def parse_data_raw_json_embed_item(self, item):
        value = self._load_json(item, item.value)
        return value
