Sample data:
-----------

qq\_sample\_db: homemade data for pre-alpha testing-as-you-go
third-party/mywind: a port of Microsoft's Northwind db from SQL Server to MySQL

Steps to prepare the cache for a database:
-----------------------------------------

1. Create these dbs manually
    `mysql -u _user_ -h _host_ -e "CREATE DATABASE foo" --password`

2. Populate using the \*.sql files found in here
    `mysql -u _user_ -h _host_ -D foo < foo.sql --password`

3. Run queries to generate schema information for the db and each of its tables
   and save the results to the Miniquery cache. The data in these files needs
   to be tab-delimited with results only, no column header; set your
   command-line flags accordingly.

``` 
    mysql -u _user_ -h _host_ -B -N -e "SELECT table_name 
        FROM information_schema.tables WHERE table_schema='_dbName_'
        ORDER BY table_name" --password=_password_  >  \
        _dbName_/information_schema.tables

    for table in $(cat _dbName_/information_schema.tables); do
        mysql -u _user_ -N -B -D _dbName_ -e "SELECT column_name, column_type,
            column_default FROM information_schema.columns
            WHERE table_schema='_dbName_' AND table_name='$table' ORDER BY
            column_name" --password=_password_  >  _dbName_/${table}.columns
    done
```

4. Run a query to summarize the table relations.

```
    mysql -B -N -u _user_ -h _host_ -e "SELECT table_name, column_name,
        referenced_table_name, referenced_column_name FROM key_column_usage
        WHERE referenced_table_name IS NOT NULL AND table_schema='_dbName_'
        ORDER BY table_name, column_name" --password=_password_  > \
        _dbName_/information_schema.key_column_usage
```