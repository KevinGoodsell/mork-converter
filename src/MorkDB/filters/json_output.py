import sys
from filterbase import Filter

class JsonOutput(Filter):
	def __init__(self):
		self.mork_filter_order = 10001

	def add_options(self, parser):
		parser.add_option('--json', dest='out_format', action='store_const',
			const='json', help='output JSON')

	def process(self, db, opts):
		if opts.out_format != 'json':
			return

		if opts.outname is None or opts.outname == '-':
			self._output(db, sys.stdout)
		else:
			with io.open(opts.outname, 'wb') as output:
				self._output(db, output)

	def _output(self, db, output):
		tables = []
		for namespace, oid, table in db.tables.items():
			meta = db.meta_tables.get((namespace, oid))
			tbl = self._process_table(namespace, oid, table, meta)
			tables.append(tbl)

		import json
		json.dump(dict(tables=tables), output)

	def _process_table(self, namespace, oid, table, meta=None):
		rows = []
		json_table = dict(
			namespace=namespace,
			id=oid,
			rows=rows,
		)

		for row_namespace, row_id, row in table:
			rows.append(self._process_row(row_namespace, row_id, row))

		if meta is not None:
			json_table['metatable'] = self._process_meta_table(meta)

		return json_table

	def _process_meta_table(self, meta):
		metacols = dict()
		for column, value in meta.cells.items():
			self._set_cell(metacols, column, value)

		metarows = []
		for namespace, oid, row in meta.rows:
			metarows.append(self._process_row(namespace, oid, row))

		return dict(
			columns=metacols,
			rows=metarows,
		)

	def _process_row(self, namespace, oid, row):
		cols = dict()
		for column, value in row.items():
			self._set_cell(cols, column, value)

		return dict(
			namespace=namespace,
			id=oid,
			columns=cols,
		)

	def _set_cell(self, row, column, value):
		assert column not in row, (column, row, value)
		row[column] = value

xml_filter = JsonOutput()
