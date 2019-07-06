Sample data
-----------

`qq_sample_db`: homemade data for pre-alpha testing-as-you-go

`third-party/mywind`: an open-source version of the Northwind database

Steps to prepare the cache for a database
-----------------------------------------

1. Create the db manually

    `mysql -u _user_ -h _host_ -e "CREATE DATABASE _dbName_" --password`

2. Populate using the \*.sql files provided
    
    `mysql -u _user_ -h _host_ -D _dbName_ < _dbName_.sql --password`

3. Run queries to generate schema information for the db and each of its tables
   and save the results to the MINIQUERY cache. The data in these files needs
   to be tab-delimited with results only, no column header, and sorted by the
   first column; set your command-line flags and queries accordingly.

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

4. Run a query to summarize the table relations. Similar formatting rules apply.

```
    mysql -B -N -u _user_ -h _host_ -e "SELECT table_name, column_name,
        referenced_table_name, referenced_column_name FROM key_column_usage
        WHERE referenced_table_name IS NOT NULL AND table_schema='_dbName_'
        ORDER BY table_name, column_name" --password=_password_  > \
        _dbName_/information_schema.key_column_usage
```
