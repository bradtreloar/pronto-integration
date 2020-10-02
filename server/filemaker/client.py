
import os
import pyodbc


class FMClient:

    def __init__(self, settings):
        self.dsn = settings["fm_dsn"]
        self.user = settings["fm_user"]
        self.password = settings["fm_password"]
        self.table = settings["fm_table"]
        fields = settings['fields']
        self.fields = fields
        self.conn = self.get_connection()
        # Collect the required columns.
        columns = []
        columns.append(fields["id"])
        columns.append(fields["ref"])
        columns.append(fields["job_name"])
        columns.append(fields["phone_number"])
        for item_fields in fields["items"]:
            columns.append(item_fields["code"])
            columns.append(item_fields["description"])
            columns.append(item_fields["quantity"])
            columns.append(item_fields["unit_price"])
        for art_fields in fields["art"]:
            columns.append(art_fields["description"])
            columns.append(art_fields["quantity"])
            columns.append(art_fields["price"])
        for payment_fields in fields["payments"]:
            columns.append(payment_fields["amount"])
            columns.append(payment_fields["invoice"])
        self.columns = ",".join(['"{}"'.format(column) for column in columns])
        # Get the list of item codes.
        item_code_filepath = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "item_codes.txt")
        self.item_codes = [line.rstrip() for line in open(item_code_filepath)]

    def get_connection(self):
        conn = pyodbc.connect(
            DSN=self.dsn,
            UID=self.user,
            PWD=self.password,
            encoding="utf-8")
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
        conn.setencoding("utf-8")
        return conn

    def get_order(self, oid):
        order = None
        error = None
        cursor = self.conn.cursor()
        # Get the job record.
        statement = 'SELECT {} FROM Allbiz WHERE "jobsheet number" = ?'.format(
            self.columns)
        cursor.execute(statement, oid)
        # Get column names
        columns = [column[0] for column in cursor.description]
        # Get the first row
        row = cursor.fetchone()
        if row:
            record = dict(zip(columns, row))
            reference = record[self.fields['ref']]
            if reference is None:
                reference = str(oid)
            # Get the part of the job name that comes before the separator
            # as this is usually the person or company's name.
            full_job_name = record[self.fields['job_name']]
            job_name = None
            if full_job_name:
                job_name = full_job_name.split(" - ")[0].strip()
            # Get the first phone number.
            full_phone_number = record[self.fields['phone_number']]
            phone_number = None
            if full_phone_number:
                phone_number = full_phone_number.split("/")[0].strip()
            order = {
                'job_name': job_name,
                'phone_number': phone_number,
                'reference': reference,
                'items': list()
            }
            # Get the items
            for field in self.fields['items']:
                item_code = record[field['code']]
                if item_code:
                    # Trim and convert to all caps.
                    item_code = item_code.strip().upper()
                    description = record[field['description']]
                    quantity = record[field['quantity']]
                    price = record[field['unit_price']]
                    if quantity is None:
                        error = "Order {} has a line ({}) with no quantity.".format(
                            str(oid), item_code)
                    # Prepend "ALL-" to code if in list
                    if item_code in self.item_codes:
                        item_code = "ALL-" + item_code
                    # Add the item to the order
                    order['items'].append({
                        'item_code': item_code,
                        'description': description,
                        'quantity': quantity,
                        'price': price,
                    })
            # Get the art
            art = 0.00
            for field in self.fields['art']:
                price = record[field['price']]
                if price:
                    price = float(price)
                    art = art + price
            if art > 0.00:
                order['items'].append({
                    'item_code': "ALL-ART",
                    'quantity': "1",
                    'price': str(art),
                })
            # Get the payments
            for field in self.fields['payments']:
                amount = record[field['amount']]
                if amount:
                    price = float(amount)
                    item = {
                        'item_code': "ALL-DEPPRINT",
                        'quantity': "-1",
                        'price': str(price),
                    }
                    invoice = record[field['invoice']]
                    if invoice:
                        item['description'] = "Paid on invoice " + \
                            str(int(invoice))
                    order['items'].append(item)
        else:
            error = "Order " + str(oid) + " not found."
        return (order, error)
