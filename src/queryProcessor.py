from sqlalchemy.sql import text

from miniUtils import QueryType
from argumentClassifier import miniArgs as args
from databaseConnection import miniDbConnection as dbConn
from errorManager import miniErrorManager as em, ReturnCode

class queryProcessor():
    # Reset or re-instantiate mbr data for every query?
    def __init__(self):
        self.query = ''
        self.queryType = QueryType.SELECT

    def process(self):
        self.inflateQuery()
        if 'q' in args.options:
            print(self.query)
        if 'r' in args.options:
            self.runAndDisplayResult()

    def inflateQuery(self):
#        self.query = "SELECT 5, 'Hello', curdate(), now(), curtime()" #'2010-05-05 01:30:00'"
#        self.query = "SELECT rateCode from table1" # WHERE id >= 3"
        self.query = "SELECT * from table1 LIMIT 4" # WHERE id >= 3"
        self.queryType = QueryType.SELECT

    def runAndDisplayResult(self):
        resultSet = dbConn.getConnection().execute(text(self.query))
        # Displaying a result set only makes sense for SELECTs
        if self.queryType != QueryType.SELECT:
            return
        #TODO: Switch to a fetchone() loop for smaller memory footprint
        rows = resultSet.fetchall()
        if not rows:
            return em.setError(ReturnCode.EMPTY_RESULT_SET)
        columnHdrs = resultSet.keys()
        if 'tab' in args.options:
            print(*columnHdrs, sep='\t')
            print('\n')
            for row in rows:
                print(*row, sep='\t')
                print('\n')
            return ReturnCode.SUCCESS
        else:
            types = resultSet._cursor_description()
            columnWidths = [max(types[i][2], len(columnHdrs[i])) # 2 = display_size
                            for i in range(len(types))]
            columnTypes = [type(rows[0][i]) for i in range(len(types))]
            # For each column, get the length of each entry and take their max
            for col in range(len(columnWidths)):
                if columnWidths[col] < 4:
                    columnHasNull = True in [not row[col] for row in rows]
                    if columnHasNull:
                        columnWidths[col] = 4
            #TODO: This is where word-wrapping would necessitate changes
            format = " ".join(["%%-%ss" % l for l in columnWidths])
            print('Format: ' + format)
            result = [format % tuple(columnHdrs)]
            result.append('\n')  # Add one blank line. This seems to add TWO.
            for row in rows:
                result.append(format % tuple([x or 'NULL' for x in row.values()]))
            print("\n".join(result))
            return ReturnCode.SUCCESS

miniQueryProcessor = queryProcessor()
