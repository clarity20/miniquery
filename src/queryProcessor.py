import os

from sqlalchemy.sql import text

from miniUtils import QueryType
from configManager import miniConfigManager as cfg
from argumentClassifier import miniArgs as args
from databaseConnection import miniDbConnection as dbConn
from errorManager import miniErrorManager as em, ReturnCode

class queryProcessor():
    # Reset or re-instantiate mbr data for every query?
    def __init__(self):
        self.query = ''
        self.queryType = QueryType.SELECT
        self.columnToSortBy = ''

    def process(self):
        self.inflateQuery()
        if 'q' in args.options:
            print(self.query)
        if 'r' in args.options:
            self.runAndDisplayResult()

    def inflateQuery(self):
        self.query = "SELECT * from table1 LIMIT 4" # WHERE id >= 3"
        self.queryType = QueryType.SELECT

    def runAndDisplayResult(self):
        resultSet = dbConn.getConnection().execute(text(self.query))

        # Displaying a result set only makes sense for SELECTs that found stg
        if self.queryType != QueryType.SELECT:
            return
        if resultSet.rowcount == 0:
            return em.setError(ReturnCode.EMPTY_RESULT_SET)

        columnHdrs = resultSet.keys()
        if 'tab' in args.options:
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
            # Fetch all rows at once. A fetchmany() loop would use less memory
            # but would not allow us to adjust the column widths for NULLs
            rows = resultSet.fetchall()
            types = resultSet._cursor_description()
            columnCount = len(types)
            columnWidths = [max(types[i][2], len(columnHdrs[i])) # [2] = display_size
                            for i in range(columnCount)]

            # If necessary, widen columns to accommodate NULLs
            for col in range(columnCount):
                if columnWidths[col] < 4:
                    columnHasNull = True in [not row[col] for row in rows]
                    if columnHasNull:
                        columnWidths[col] = 4

            # Wrapless or word-wrapped printout
            screenWidth, b = os.get_terminal_size()
            if 'nowrap' in args.options or sum(columnWidths) + columnCount < screenWidth:
                format = " ".join(["%%-%ss" % l for l in columnWidths])
                result = [format % tuple(columnHdrs)]
                result.append('')
                for row in rows:
                    result.append(format % tuple([x or 'NULL' for x in row.values()]))
                print("\n".join(result))
                return ReturnCode.SUCCESS
            else:
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

miniQueryProcessor = queryProcessor()
