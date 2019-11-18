# -*- coding: utf-8 -*-
from future import standard_library
standard_library.install_aliases()
from builtins import str
from io import StringIO

from flask import Flask
from flask.ext.testing import TestCase
from json import dumps
from json import loads
from nose.plugins.skip import SkipTest

import rest

from test import ViewTestCase

from rest.schema import Schema


class TestRest(ViewTestCase):

  def test_simple_serialize(self):
    self.assertEquals('{"simple": "json"}', rest._serialize({'simple': 'json'}))
    self.assertEquals('["a list", 1]', rest._serialize(["a list", 1]))


class TestSimpleApp(TestCase):
  def setUp(self):
    self.last_post = None

    @self.app.route('/post', methods=['POST'])
    @rest.view
    def post(data):
      self.last_post = data
      return dict(data)

  def create_app(self):
    self.app = Flask('TestSimpleApp')
    return self.app

  def test_utf8_body(self):
    body = '{"hi": "Nina\u2019s"}'
    resp = self.client.post('/post', data=body)
    self.assert200(resp)

    self.assertEquals(u'Nina\u2019s', loads(resp.data)['hi'])
    self.assertEquals(u'Nina\u2019s', self.last_post['hi'])

  def test_unicode_without_encoding_header(self):
    raise SkipTest
    body = u'{"hi": "L\u2019Acadie pour Elle"}'
    resp = self.client.post('/post', data=body)
    self.assertEquals(400, resp.status_code)
    body = loads(resp.data)
    self.assertEquals({
      'client': ['Expecting property name: line 1 column 1 (char 1)']
    }, body)


class TestCSVUpload(TestCase):
  def setUp(self):
    self.seen_dog_names = []

    self.csv_headers = {
      'content-type': 'multipart/form-data'
    }

    class CSVSchema(Schema):
      dog_type = rest.String(validators=[rest.nonempty])
      food     = rest.String(validators=[rest.nonempty])
      pounds   = rest.Int()


    @self.app.route('/csv', methods=['POST'])
    @rest.csv_upload(CSVSchema)
    def csv(rows):
      for schema in rows:
        self.seen_dog_names.append(schema.dog_type.get())
      return rest.created({'csv': 'created'})

    @self.app.route('/csv_with_fieldnames', methods=['POST'])
    @rest.csv_upload(CSVSchema, fieldnames=('dog_type','food','pounds',))
    def csv_with_fieldnames(rows):
      for schema in rows:
        self.seen_dog_names.append(schema.dog_type.get())
      return rest.created({'csv': 'created'})

    @self.app.route('/csv_json/<id_one>/<id_two>', methods=['POST'])
    @rest.json_csv_upload(('dog_type','food','pounds',))
    def csv_json(id_one, id_two, rows, data):
      errors   = {}
      response = []

      for row, row_number, errors in rows:
        if errors:
          errors[row_number] = errors
        else:
          response.append(row)

      if errors:
        return rest.error(errors)
      else:
        return rest.created(response)

  def create_app(self):
    self.app = Flask('TestCSVUpload')
    return self.app

  def test_csv_upload_with_empty_request_body(self):
    """
    it should 400 if no expecting csv but got empty body
    """
    resp = self.client.post('/csv', headers=self.csv_headers)

    self.assert400(resp)

  def test_csv_upload_without_header(self):
    """
    it should 400 if it doesn't know which fields to use for rows
    """
    data = "great dane,cured meats,200\n" \
      "shibe,doge food,20\n" \
      "'strodog,kibble,65"

    resp = self.client.post('/csv', data={
      'file': (StringIO(data), 'test.csv')}, headers=self.csv_headers)

    self.assert400(resp)
    body = loads(resp.data)

    self.assertIn('cannot be empty', body['food'])

  def test_csv_upload_with_invalid_data(self):
    """
    it should 400 if data being upload violates schema, returning errors by
    column name
    """
    data = "dog_type,food,pounds\n" \
      "great dane,cured meats,200\n" \
      "cerberus,,1500\n" \
      "shibe,doge food,20\n" \
      "'strodog,kibble,65"

    resp = self.client.post('/csv', data={
      'file': (StringIO(data), 'test.csv')}, headers=self.csv_headers)

    self.assert400(resp)
    body = loads(resp.data)

    self.assertIn('cannot be empty', body['food'])

  def test_csv_upload_with_valid_data(self):
    data = "dog_type,food,pounds\n" \
      "great dane,cured meats,200\n" \
      "cerberus,souls,1500\n" \
      "shibe,doge food,20\n" \
      "'strodog,kibble,65"

    resp = self.client.post('/csv', data={
      'file': (StringIO(data), 'test.csv')}, headers=self.csv_headers)

    self.assert_status(resp, 201)

  def test_csv_upload_with_valid_data_gives_view_rows_generator(self):
    """
    it should give the view function a rows generator object which yields one
    rest.Schema for each row
    """
    data = "dog_type,food,pounds\n" \
      "great dane,cured meats,200\n" \
      "cerberus,live meat ONLY,1500\n" \
      "shibe,doge food,20\n" \
      "'strodog,kibble,65\n"

    resp = self.client.post('/csv', data={
      'file': (StringIO(data), 'test.csv')}, headers=self.csv_headers)

    self.assert_status(resp, 201)

    expected_dog_names = ('great dane', 'cerberus', 'shibe', "'strodog")
    self.assertEqual(4, len(self.seen_dog_names))

    for name in self.seen_dog_names:
      self.assertIn(name, expected_dog_names)

  def test_csv_upload_with_unicode_body(self):
    """
    it should be able to handle unicode characters
    """
    data = "dog_type,food,pounds\n" \
      "foxes,cured meats,3200\n" \
      "H\xc3\xa4nsel,pies,1500\n" \
      "ni\xc3\xb1o,foods,43\n"

    resp = self.client.post('/csv',
      data={'file': (StringIO(data), 'test.csv')},
      headers=self.csv_headers)

    self.assert_status(resp, 201)
    self.assertIn(u'Hänsel', self.seen_dog_names)
    self.assertIn(u'niño', self.seen_dog_names)
    self.assertIn(u'foxes', self.seen_dog_names)

  def test_json_csv_upload_with_no_csv_key(self):
    headers = {
      'content-type': 'text/json'
    }

    data = "foxes,cured meats,3200\n" \
      "H\xc3\xa4nsel,pies,1500\n" \
      "ni\xc3\xb1o,foods,43\n"

    o = {
      'this_key_isnt_called_csv': data
    }

    resp = self.client.post('/csv_json/h/f', data=dumps(o), headers=headers)
    self.assert400(resp)

    body = loads(resp.data)

    self.assertIn('"csv" key cannot be empty', body['client'])

  def test_json_csv_upload(self):
    """
    it should handle request bodies like {"csv": "name,a,b\nhonk,c,d"}
    """
    headers = {
      'content-type': 'text/json'
    }

    data = "foxes,cured meats,3200\n" \
      "H\xc3\xa4nsel,pies,1500\n" \
      "ni\xc3\xb1o,foods,43\n"

    o = {
      'csv': data
    }

    resp = self.client.post('/csv_json/some_id/some_other',
        data=dumps(o), headers=headers)
    self.assert_status(resp, 201)

    body = loads(resp.data)

    names = [d.get('dog_type') for d in body]

    self.assertIn(u'Hänsel', names)
    self.assertIn(u'niño', names)
    self.assertIn(u'foxes', names)

  def test_json_csv_with_defined_fieldnames(self):
    """
    it should use the given fieldnames in making dicts for the schema
    """
    data = '''foxes,cured meats,3200\n''' \
      '''geese,pies,1500\n''' \
      '''pigs,errything,43\n''' \
      '''"fast horses",race food,33\n''' \
      '''"slow horses",grass food,33'''

    o = {
      'csv': str(data)
    }

    fieldnames = ('name','feed','pounds',)
    @rest.json_csv_upload(fieldnames)
    def test_using_defined_column_names(rows, data):
      seen_keys = set()
      seen_rows = []

      for row, row_number, errors in rows:
        seen_rows.append(row)
        for k in list(row.keys()):
          seen_keys.add(k)

      self.assertEqual(3, len(seen_keys))
      self.assertIn('name', seen_keys)
      self.assertIn('feed', seen_keys)
      self.assertIn('pounds', seen_keys)

      self.assertEquals('foxes', seen_rows[0].get('name'))
      self.assertEquals('geese', seen_rows[1].get('name'))
      self.assertEquals('pigs', seen_rows[2].get('name'))
      self.assertEquals('fast horses', seen_rows[3].get('name'))
      self.assertEquals('slow horses', seen_rows[4].get('name'))

      self.assertEquals('cured meats', seen_rows[0].get('feed'))
      self.assertEquals('pies', seen_rows[1].get('feed'))
      self.assertEquals('errything', seen_rows[2].get('feed'))
      self.assertEquals('race food', seen_rows[3].get('feed'))
      self.assertEquals('grass food', seen_rows[4].get('feed'))

      self.assertEquals('3200', seen_rows[0].get('pounds'))
      self.assertEquals('1500', seen_rows[1].get('pounds'))
      self.assertEquals('43', seen_rows[2].get('pounds'))
      self.assertEquals('33', seen_rows[3].get('pounds'))
      self.assertEquals('33', seen_rows[4].get('pounds'))

    test_using_defined_column_names(data=o)

  def test_json_csv_with_differing_fieldnames_and_row_lengths(self):
    """
    it should yield an errors list from the returned generator with a message
    about the row length if too many or too few columns in data
    """
    data = '''foxes,cured meats,3200\n''' \
      '''H\xc3\xa4nsel,pies,1500,5\n''' \
      '''ni\xc3\xb1o,foods,43\n''' \
      '''"quotes, mc",,33\n''' \
      '''"quotes, mc",rt,33,honk,"honk"'''

    o = {
      'csv': data
    }

    @rest.json_csv_upload(('dog_name','food','pounds',))
    def test_yielded_errors(rows, data):
      collected_errors = []
      for row, row_number, errors in rows:
        collected_errors.append(errors)

      self.assertIn('Expecting 3 columns in row 2, got 4', collected_errors[1])
      self.assertIn('Expecting 3 columns in row 5, got 5', collected_errors[4])

    test_yielded_errors(data=loads(dumps(o)))
