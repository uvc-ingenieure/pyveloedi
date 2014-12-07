#!/usr/bin/env python
from pyveloedi import VeloContext, WinoraContext
import sys

VELOCONNECT_URL = 'http://boettcher.veloconnect.de'
VELOCONNECT_USER = sys.argv[1]
VELOCONNECT_PASSWD = sys.argv[2]

def main():
    context = VeloContext(url=VELOCONNECT_URL, userid=VELOCONNECT_USER,
                          passwd=VELOCONNECT_PASSWD, istest=False, log=False)
    EDIProduct = context.get('Product')
    EDIOrder = context.get('Order')

    # Search the product model.
    # If count == True it will return the count of found records, otherwise a
    # list of primaries of the found records.
    product_ids = EDIProduct.search(['glocke'], offset=0, limit=10, count=False)

    # Fetch the product details of the found primaries.
    products = EDIProduct.read(product_ids)
    order_lines = []
    print 'SEARCH RESULT'
    for ep in products:
        print '%s %s %s %s' % (ep.code, ep.list_price, ep.cost_price, ep.name)
        code = ep.code
        if ep.valid:
            # Add product to lines to order if valid
            # Lines is a list of tuples with (EDIProduct, Quantity)
            order_lines.append((ep, 1))


    # Then create order to get concrete availability
    order = EDIOrder.create(order_lines)
    print '\nORDER LINES'
    for line in order.lines:
        code = line.product.code
        print 'code: %s available quantity: %s state: %s' % (
            line.product.code,
            line.available_quantity,
            line.availability)

    # We actually don't want to place a real order.
    # Beware: Even if a test mode exists and it's implemented, some
    #         suppliers don't respect it.
    # order.finish()

if __name__ == '__main__':
    main()
