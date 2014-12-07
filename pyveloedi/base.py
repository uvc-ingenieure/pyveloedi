# The MIT License (MIT)
#
# Copyright (c) 2014 Max Holtzberg <mh@uvc.de>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import decimal
from lxml import etree
import re
import sys
import urllib2


class Field(object):
    def __init__(self, *args, **kwargs):
        self._default = kwargs.get('default', None)
        self._args = args
        self._kwargs = kwargs

    def parse(self, rec):
        for prefix in [''] + rec._prefixes:
            for path in self._args:
                node = rec._data.find(prefix + path, namespaces=rec._namespaces)
                if node is not None:
                    return self._convert(node)

        return self._default


class Bool(Field):
    _neg = False
    def _convert(self, node):
        if 'equals' in self._kwargs:
            res = self._kwargs['equals'] == node.text
        else:
            res = bool(node.text)
        return res ^ self._neg

    def __invert__(self):
        self._neg = True
        return self


class String(Field):
    def __init__(self, *args, **kwargs):
        super(String, self).__init__(*args, **kwargs)
        if 'subst' in kwargs:
            exp, self._sub = kwargs['subst']
            self._exp = re.compile(exp)
        else:
            self._exp = None

    def _convert(self, node):
        if self._exp is None:
            return unicode(node.text)
        else:
            return self._exp.sub(self._sub, node.text)


class Integer(Field):
    def _convert(self, node):
        return int(node.text)


class Decimal(Field):
    def _convert(self, node):
        return decimal.Decimal('%.2f' % decimal.Decimal(
                node.text.replace(',', '.')))


class URL(Field):
    def _convert(self, node):
        return buffer(urllib2.urlopen(node.text).read())


class One2Many(Field):
    def parse(self, rec):
        for path in self._args:
            items = rec._data.xpath(path, namespaces=rec._namespaces)
            if len(items) > 0:
                return self._convert(items)

        if self._default is None:
            return []
        return self._default

    def _convert(self, items):
        return map(self._kwargs['model'], items)


class Many2One(Field):
    def parse(self, rec):
        if len(self._args) <= 0:
            return self._convert(rec._data)
        return super(Many2One, self).parse(rec)

    def _convert(self, node):
        return self._kwargs['model'](node)

class Attribute(Field):
    def _convert(self, node):
        return node.get(self._kwargs['attr'])


class Model(object):
    _namespaces = {}
    _prefixes = []
    valid = Bool(default=False)

    def __init__(self, data, context=None):
        if isinstance(data, etree._Element):
            self._data = data
            self._ctx = context
        else:
            self._load(data)

    def _load(self, data):
        # Fill instance from data, maybe a primary key
        raise NotImplementedError()

    def __getattribute__(self, name):
        attr = super(Model, self).__getattribute__(name)
        if isinstance(attr, Field):
            return attr.parse(self)
        return attr

    @classmethod
    def copy(cls, context):
        Class = type(cls.__name__, cls.__bases__, dict(cls.__dict__))
        Class._ctx = context
        return Class


    @classmethod
    def search(cls, keywords, offset=0, limit=20, count=False):
        raise NotImplementedError()

    @classmethod
    def read(cls, codes):
        raise NotImplementedError()

    @classmethod
    def create(cls, records):
        raise NotImplementedError()

    @classmethod
    def update(cls, records):
        raise NotImplementedError()


class ProductBase(Model):
    name = Field()
    description = Field()
    code = Field()
    replacement = Field()
    ean13 = Field()
    list_price = Field()
    cost_price = Field()
    picture = Field()
    manufacturer = Field()

    @property
    def availability(self):
        return None


class OrderBase(Model):
    orderid = Field()
    lines = Field()


class EDIException(Exception):
    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._msg

    def __str__(self):
        return repr(self._msg)


class ContextBase(object):
    def __init__(self, url, userid, passwd, log=False):
        self._url = url
        self._userid = userid
        self._passwd = passwd
        self._log = log

    def log(self, info, msg):
        if self._log:
            frame = sys._getframe(1)
            cls = frame.f_locals.get('self', False)
            cls = cls.__class__.__name__ + '.' if cls else ''

            print '[ @%s%s (%s) ]' % (cls, frame.f_code.co_name, info)
            print msg + '\n'

    def get(self, clsname):
        raise NotImplementedError()

    def connect(self):
        raise NotImplementedError()

    def get_product(self, code):
        raise NotImplementedError()

    def check(self):
        raise NotImplementedError()
