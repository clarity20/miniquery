import os
import re
from sqlalchemy.sql import text

from miniUtils import QueryType
from configManager import masterDataConfig as cfg
from databaseConnection import miniDbConnection as dbConn
from errorManager import miniErrorManager as em
from errorManager import ReturnCode
from argumentClassifier import ArgumentClassifier

class QueryProcessor:

    def __init__(self, arguments):
        self.query = ''
        self._queryType = QueryType.OTHER
        self._columnToSortBy = ''
        self._arguments = arguments

    def process(self, literalSql=''):
        em.resetError()
        ret = ReturnCode.SUCCESS
        if literalSql:
            self.query = literalSql

            # When literal SQL is provided, assume user does not need it echoed
            self._arguments._options.pop('q', None)

            # For implicit queries, figure out the query type
            firstWord = literalSql.partition(' ')[0].lower()
            if firstWord in ['select', 'show', 'desc']:
                self._queryType = QueryType.SELECT
            elif firstWord == 'update':
                self._queryType = QueryType.UPDATE
            elif firstWord == 'delete':
                self._queryType = QueryType.DELETE
            elif firstWord == 'insert':
                self._queryType = QueryType.INSERT
        else:
            self._queryType = self.deduceQueryType()
            ret = em.getError()
            if ret == ReturnCode.INCONSISTENT_QUERY_TYPES:
                return ret

            ret = self.inflateQuery()
            if ret != ReturnCode.SUCCESS:
                return ret

        # The query is now fully inflated and ready to be shown and/or run.
        if 'q' in self._arguments._options:
            print(self.query)
        if 'r' in self._arguments._options:
            ret = self.runAndDisplayResult()
            if ret != ReturnCode.SUCCESS:
                return ret
        return ret

    def deduceQueryType(self):
        '''
        Deduce the query type from the two indicators and ensure they are consistent.
        The indicators are (1) the command name / query type option flag and
        (2) the modification operators (if any) appearing in the query particles.
        Note: SELECT queries should not have modification operators.
        '''

        # Note the command name or the query-type option flag and the query type thereby implied
        cmdName = self._arguments._commandName
        if cmdName:
            indicator1, typeHint1 = cmdName, getattr(QueryType, cmdName.upper())
        elif 'i' in self._arguments._options:
            indicator1, typeHint1 = '-i', QueryType.INSERT
        elif 'u' in self._arguments._options:
            indicator1, typeHint1 = '-u', QueryType.UPDATE
        elif 'd' in self._arguments._options:
            indicator1, typeHint1 = '-d', QueryType.DELETE
        #TODO Consider adding option flags for non-DML query types
        else:
            # No flag for SELECTs since they are the default.
            # Consider the  query type to be unidentified thus far
            indicator1, typeHint1 = 'select', QueryType.OTHER

        # Note any modification operators and the query types thereby implied
        indicator2, typeHint2 = 'select', QueryType.OTHER
        op = None
        for o in self._arguments._operators:
            previousIndicator2, previousHint2 = op, typeHint2
            op = o._operator
            # Convention: DML operators have length 2, DDL have length 3
            if len(op) == 2:
                if op == '.=':
                    indicator2, typeHint2 = op, QueryType.INSERT
                elif op == '\=':
                    # The DELETE operator. To the user it doesn't make a whole lot of sense
                    # semantically unless it stands alone in its containing argument, which
                    # makes it redundant with the type hint already examined above.
                    #TODO: Let us accept it in both safety modes but require it only in "safe mode".
                    indicator2, typeHint2 = op, QueryType.DELETE
                elif re.fullmatch(r'[:+\-*/%]=', op):
                    indicator2, typeHint2 = op, QueryType.UPDATE
            else:
                # Operator length > 2. This means it's a DDL command or it's
                # one of the obscure arithmetic update operators <<= or >>=.
                #TODO: Fill this in later
                pass

            # If some operators indicate different query types, it's an error
            if typeHint2 != previousHint2 and previousHint2 != QueryType.OTHER:
                return em.setError(ReturnCode.INCONSISTENT_QUERY_TYPES, previousIndicator2, op)

        # Once all the operators have been examined, if the type is still marked
        # OTHER then there there were NO operators. SELECTs, and only SELECTs,
        # have no operators.
        if typeHint1 == QueryType.OTHER and typeHint2 == QueryType.OTHER:
            queryType = QueryType.SELECT
        elif typeHint1 == typeHint2:
            queryType = typeHint2
        else:
            return em.setError(ReturnCode.INCONSISTENT_QUERY_TYPES, indicator1, indicator2)

        return queryType


    def inflateQuery(self):
        self.query = "SELECT * from customers LIMIT 4" #TODO MMMM WHERE id >= 3"
        self._queryType = QueryType.SELECT
        return ReturnCode.SUCCESS

    def runAndDisplayResult(self):
        conn = dbConn.getConnection()
        if em.getError() != ReturnCode.SUCCESS:
            return em.getError()

        # Try to execute the query, handling any exceptions thrown by the API.
        # Further information about exceptions is available in the SQLAlchemy help and website.
        from sqlalchemy.exc import DBAPIError
        try:
            resultSet = conn.execute(text(self.query))
        except DBAPIError as e:
            return em.setException(e, "Error/exception thrown by %s driver" % dbConn.getDialect())

        # Displaying a result set only makes sense for SELECTs that found stg
        if self._queryType != QueryType.SELECT:
            return ReturnCode.SUCCESS
        if resultSet.rowcount == 0:
            return em.setError(ReturnCode.EMPTY_RESULT_SET)

        columnHdrs = resultSet.keys()
        columnCount = len(columnHdrs)
        if 'tab' in self._arguments._options:
            print(*columnHdrs, sep='\t')
            format = '\t'.join(['%s']*columnCount)
            while True:
                # don't use too much memory
                rows = resultSet.fetchmany()
                if not rows:
                    break
                for row in rows:
                    print(format % tuple(v or 'NULL' for v in row.values()))
            return ReturnCode.SUCCESS
        else:
            types = resultSet._cursor_description()
            columnWidths = [max(types[i][2], len(columnHdrs[i])) # [2] = display_size
                            for i in range(columnCount)]

            if 'vertical' in self._arguments._options:
                nameWidth = max([len(columnHdrs[i]) for i in range(columnCount)])
                # Format is "column header : value" repeated over the columns.
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
                        print(format % tuple(v or 'NULL' for v in row.values()))
                        count += 1

                return ReturnCode.SUCCESS

            # Fetch all rows at once. A fetchmany() loop would use less memory
            # but would not allow us to adjust the column widths for NULLs
            rows = resultSet.fetchall()

            # If necessary, widen columns to accommodate NULLs
            for col in range(columnCount):
                if columnWidths[col] < 4:
                    columnHasNull = True in [not row[col] for row in rows]  #TODO "not..." is suspicious!
                    if columnHasNull:
                        columnWidths[col] = 4

            # Wrapless or word-wrapped printout
            try:
                screenWidth, b = os.get_terminal_size()
            except OSError:
                # Screen width is unavailable when stdout is not a tty (i.e. redirection)
                screenWidth = 999999
            if 'nowrap' in self._arguments._options or sum(columnWidths) + columnCount < screenWidth:
                format = " ".join(["%%-%ss" % l for l in columnWidths])
                result = [format % tuple(columnHdrs)]
                result.append('')
                for row in rows:
                    result.append(format % tuple([v or 'NULL' for v in row.values()])) #TODO "NULL" is suspicious!
                print("\n".join(result))
                return ReturnCode.SUCCESS
            elif 'wrap' in self._arguments._options:
                # Choose a helper column to make the wrap more readable
                from appSettings import miniSettings; ms = miniSettings
                try:
                    dbCfg = cfg.databases[ms.settings['Settings']['database']]
                    tableCfg = dbCfg.tables[ms.settings['Settings']['table']]
                except KeyError:
                    pass
                if self._columnToSortBy:
                    # Look up the sorting column in the header by name. For this
                    # to work in the case of aliases, the sort column must hold
                    # the alias name, not the true name
                    helpColumn = columnHdrs.index(self._columnToSortBy)
                elif tableCfg and tableCfg.config['primaryColumn']:
                    helpColumn = columnHdrs.index(tableCfg.config['primaryColumn'])
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

class HiddenQueryProcessor(QueryProcessor):
    '''
    A processor for running "under the hood" queries not explicitly entered as commands
    '''

    def __init__(self):
        arguments = ArgumentClassifier().addOption('r')
        super().__init__(arguments)

