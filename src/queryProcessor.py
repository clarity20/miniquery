import os

from sqlalchemy.sql import text

from miniUtils import QueryType
from configManager import miniConfigManager as cfg
from databaseConnection import miniDbConnection as dbConn
from errorManager import miniErrorManager as em, ReturnCode

class queryProcessor:

    def __init__(self, arguments):
        self.query = ''
        self.queryType = QueryType.SELECT
        self.columnToSortBy = ''
        self.arguments = arguments

    def process(self, sql=''):
        ret = ReturnCode.SUCCESS
        if sql:
            self.query = sql
        else:
            ret = self.inflateQuery()
            if ret != ReturnCode.SUCCESS:
                return ret
        if 'q' in self.arguments.options:
            print(self.query)
        if 'r' in self.arguments.options:
            ret = self.runAndDisplayResult()
            if ret != ReturnCode.SUCCESS:
                return ret
        return ret

    def inflateQuery(self):
        self.query = "SELECT * from table1 LIMIT 4" #MMMM WHERE id >= 3"
        self.queryType = QueryType.SELECT

    def runAndDisplayResult(self):
        conn = dbConn.getConnection()
        if em.getError() != ReturnCode.SUCCESS:
            return em.getError()
        resultSet = conn.execute(text(self.query))

        # Displaying a result set only makes sense for SELECTs that found stg
        if self.queryType != QueryType.SELECT:
            return
        if resultSet.rowcount == 0:
            return em.setError(ReturnCode.EMPTY_RESULT_SET)

        columnHdrs = resultSet.keys()
        if 'tab' in self.arguments.options:
            print(*columnHdrs, sep='\t')
            while True:
                # don't use too much memory
                rows = resultSet.fetchmany()
                if not rows:
                    break
                for row in rows:
                    print(*row, sep='\t')
            return ReturnCode.SUCCESS
        else:
            types = resultSet._cursor_description()
            columnCount = len(types)
            columnWidths = [max(types[i][2], len(columnHdrs[i])) # [2] = display_size
                            for i in range(columnCount)]

            if 'vertical' in self.arguments.options:
                nameWidth = max([len(columnHdrs[i]) for i in range(columnCount)])
                # Format is "column name : value" repeated over the columns.
                # In the next line we precompute the format pieces and concat.
                format = '\n'.join(['{0:>{width}}: %s'.
                            format(h, width=nameWidth) for h in columnHdrs])
                count = 0
                while True:
                    rows = resultSet.fetchmany()
                    if not rows:
                        break
                    for row in rows:
                        # The banner: * is fill, ^ is centering, 62 is width,
                        # all to mimic mysql's behavior
                        print('{0:*^62}'.format(' %d. row ' % count))
                        # The data: write the values into the prepared format
                        print(format % tuple(row.values()))
                        count += 1

                return ReturnCode.SUCCESS

            # Fetch all rows at once. A fetchmany() loop would use less memory
            # but would not allow us to adjust the column widths for NULLs
            rows = resultSet.fetchall()

            # If necessary, widen columns to accommodate NULLs
            for col in range(columnCount):
                if columnWidths[col] < 4:
                    columnHasNull = True in [not row[col] for row in rows]
                    if columnHasNull:
                        columnWidths[col] = 4

            # Wrapless or word-wrapped printout
            screenWidth, b = os.get_terminal_size()
            if 'nowrap' in self.arguments.options or sum(columnWidths) + columnCount < screenWidth:
                format = " ".join(["%%-%ss" % l for l in columnWidths])
                result = [format % tuple(columnHdrs)]
                result.append('')
                for row in rows:
                    result.append(format % tuple([x or 'NULL' for x in row.values()]))
                print("\n".join(result))
                return ReturnCode.SUCCESS
            elif 'wrap' in self.arguments.options:
                # Choose a helper column to make the wrap more readable
                if self.columnToSortBy:
                    # Look up the sorting column in the header by name. For this
                    # to work in the case of aliases, the sort column must hold
                    # the alias name, not the true name
                    helpColumn = columnHdrs.index(self.columnToSortBy)
                elif cfg.config['primaryColumn']:
                    helpColumn = columnHdrs.index(cfg.config['primaryColumn'])
                else:
                    helpColumn = 0
                helpColumnName = columnHdrs[helpColumn]

                # Wrap repeatedly until done
                lastColumn = -1
                includeHelp = False   # Do not alter top row with help column
                finishedWrapping = False
                while not finishedWrapping:

                    # Initialize the next text block
                    lastColumn = firstColumn = lastColumn + 1
                    totalWidth = 0
                    if includeHelp:
                        totalWidth = columnWidths[helpColumn] + 1

                    # Decide what columns will be included
                    while True:
                        # Omit help if it would be too close to itself
                        if includeHelp and lastColumn - firstColumn < 3 \
                        and helpColumnName == columnHdrs[lastColumn]:
                            totalWidth -= columnWidths[helpColumn] + 1
                            includeHelp = False
                        # Check the proposed width against the constraint
                        newWidth = totalWidth + columnWidths[lastColumn] + 1
                        if newWidth > screenWidth:
                            if lastColumn > firstColumn:
                                # Toss the last column and don't update width
                                lastColumn -= 1
                                break
                            else:
                                # Toss the help but keep the column no matter its width
                                if includeHelp:
                                    totalWidth -= columnWidths[helpColumn] + 1
                                    includeHelp = False
                                    print('last: ' + str(lastColumn) + ' count: ' + str(columnCount))
                                    if lastColumn == columnCount - 1:
                                        finishedWrapping = True
                                        break
                                break
                        else:
                            totalWidth = newWidth
                            if lastColumn == columnCount - 1:
                                finishedWrapping = True
                                break
                            else:
                                lastColumn += 1
                                # Do not break

                    # Print the text block
                    columnList = [helpColumn] + list(range(firstColumn, lastColumn+1)) \
                            if includeHelp else list(range(firstColumn, lastColumn+1))
                    format = " ".join(["%%-%ss" % columnWidths[i] for i in columnList])
                    result = [format % tuple(columnHdrs[i] for i in columnList)]
                    result.append('')
                    for row in rows:
                        v = row.values()
                        result.append(format % tuple([v[i] or 'NULL' for i in columnList]))
                    result.append('')
                    print("\n".join(result))
                    columnList.clear()
                    if finishedWrapping:
                        break

                    # Turn help on by default for the next chunk
                    includeHelp = True

                # The result has been fully printed out in chunks
                return ReturnCode.SUCCESS

