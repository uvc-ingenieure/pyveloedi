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

import copy
import urllib2
from lxml import etree
import urllib

from .base import ProductBase, ContextBase, OrderBase, EDIException, Model
import base

BASKETNAME = 'warenkorb'

class WinoraException(EDIException):
    def __init__(self, msg):
        self._code = 0
        self._msg = msg


class InvalidProduct(ProductBase):
    def __init__(self, code):
        self._code = code

    @property
    def code(self):
        return self._code


class Context(ContextBase):
    def get(self, clsname):
        if clsname == 'Product':
            return Product.copy(self)
        elif clsname == 'Order':
            return Order.copy(self)
        return None

    def dispatch_request(self, request):
        args = request.get_url_args()
        root = etree.fromstring(self.execute(args))
        self.log('XML Response', etree.tostring(root, pretty_print=True))
        msg, = root.xpath('/root/processmessage')
        if msg.text != 'ok':
            raise WinoraException(msg.text)
        return root

    def execute(self, params):
        params = [('loginid', self._userid),
                   ('password', self._passwd)] + params
        self.log('Args', str(params))
        url = '%s?%s' % (self._url, urllib.urlencode(params))
        return urllib2.urlopen(url).read()

    def check(self):
        vi = VersionInfo(self)
        try:
            etree.tostring(vi.execute(), pretty_print=True)
        except:
            return False
        return True


class WinoraBase(object):
    def __init__(self, context):
        self._ctx = context


class VersionInfo(WinoraBase):
    def get_url_args(self):
        return [('processtype', 'versioninfo')]

    def execute(self):
        return self._ctx.dispatch_request(self)


class ItemDetails(WinoraBase):
    def get_url_args(self):
        return [('processtype', 'itemdetails'),
                ('pagesize', 100)] + [('itemnumber', c) for c in self._codes]

    def execute(self, codes):
        self._codes = codes
        root = self._ctx.dispatch_request(self)
        items = root.xpath('/root/item')
        return map(Product, items)


class SearchProducts(WinoraBase):
    def get_url_args(self):
        return [('processtype', 'searchcatalog'),
                ('pagesize', self._limit),
                ('page', self._page),
                ('searchpattern', ' '.join(self._keywords).encode('utf-8') )]

    def execute(self, keywords, offset, limit):
        self._keywords = keywords
        self._limit = limit
        self._page = int(offset / limit)
        root = self._ctx.dispatch_request(self)
        items = root.xpath('/root/item')
        return map(Product, items)


class DeleteBasket(WinoraBase):
    def get_url_args(self):
        return [('processtype', 'delbasket'), ('basketname', BASKETNAME)]

    def execute(self):
        return self._ctx.dispatch_request(self)


class Basket(WinoraBase):
    def get_url_args(self):
        res = [('processtype', 'basket'), ('basketname', BASKETNAME)]
        for line in self._lines:
            res.append(('itemquantity.' + line[0].code, int(line[1])))
        return res

    def execute(self, lines):
        self._lines = lines
        self._ctx.dispatch_request(self)


class ViewBasket(WinoraBase):
    def get_url_args(self):
        return [('processtype', 'viewbasket'), ('basketname', BASKETNAME)]

    def execute(self):
        return self._ctx.dispatch_request(self)


class OrderBasket(WinoraBase):
    def get_url_args(self):
        return [('processtype', 'orderbasket'), ('basketname', BASKETNAME)]

    def execute(self):
        root = self._ctx.dispatch_request(self)
        res, = root.xpath('/root/ordernumber')
        return unicode(res.text)


class Product(ProductBase):
    name = base.String('description1')
    code = base.String('number')
    ean13 = base.String('ean')
    list_price = base.Decimal('recommendedretailprice')
    cost_price = base.Decimal('unitprice')
    manufacturer = base.String('supplier')
    picture = base.URL('pictureurl')

    @property
    def valid(self):
        return True

    @property
    def description(self):
        descr = base.String('description2').parse(self)
        if descr is None:
            return self.name
        return descr

    @classmethod
    def search(cls, keywords, offset=0, limit=20, count=False):
        if limit is None:
            limit = 20

        sp = SearchProducts(cls._ctx)
        products = sp.execute(keywords, offset, limit)
        if count:
            if len(products) < limit:
                return len(products)
            else:
                # HACK
                return 100 * limit

        return [p.code for p in products]

    @classmethod
    def read(cls, codes):
        if len(codes) == 0:
            return []

        # If products dont exist, create invalid products.
        # All for all codes coming in, products have to be returned.
        itd = ItemDetails(cls._ctx)
        products = {}
        for product in itd.execute(codes):
            products[product.code] = product

        res = []
        for code in codes:
            if code in products:
                res.append(products[code])
            else:
                res.append(InvalidProduct(code))

        return res


class Line(Model):
    product = base.Many2One(model=Product)
    quantity = base.Decimal('quantity')
    available_quantity = base.Decimal('availablequantity')

    @property
    def availability(self):
        if self.available_quantity >= self.quantity:
            return 'available'
        elif self.available_quantity > 0:
            return 'partially_available'
        else:
            return 'not_available'


class Order(OrderBase):
    lines = base.One2Many('/root/item', model=Line)

    @classmethod
    def create(cls, lines):
        return Order(lines, context=cls._ctx)

    def __init__(self, lines, context):
        self._lines = lines
        self._ctx = context
        self._data = None
        self._synch()

    def _synch(self):
        db = DeleteBasket(self._ctx)
        db.execute()
        basket = Basket(self._ctx)
        basket.execute(self._lines)
        vb = ViewBasket(self._ctx)
        self._data = vb.execute()

    def add_lines(self, lines):
        cls._lines += lines
        self._synch()

    @property
    def orderid(self):
        return self._orderid

    def finish(self):
        ob = OrderBasket(self._ctx)
        self._orderid = ob.execute()

