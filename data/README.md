Sample data
-----------

`qq_sample_db`: very small, basic database

`third-party/mywind`: an open-source version of the Northwind database

`sakila`
`world` : sample DBs provided with the mysql 8.x download

Steps to prepare the cache for a database
-----------------------------------------

PLEASE NOTE: (1) and (2) apply only to the sample databases provided.
To configure MINIQUERY for your own data, go directly to (3).

1. Create the db manually:

    `mysql -u ${user} -h ${host} -e "CREATE DATABASE ${dbName}" --password`

2. Populate the db using the \*.sql files provided.
    
    `mysql -u ${user} -h ${host} -D ${dbName} < ${dbName}.sql --password`

3. Run queries to generate schema information for the db and each of its tables
   and save the results to the MINIQUERY cache. The data in these files needs
   to be tab-delimited with results only (no column header) and sorted by the
   first column; set your command-line flags and queries accordingly.

``` 
    mysql -u ${user} -h ${host} -B -N -e "SELECT table_name
        FROM information_schema.tables WHERE table_schema='${dbName}'
        ORDER BY table_name" --password=${password}  >  \
        ${MINI_CACHE}/${dbName}/information_schema.tables

    for table in $(cat ${dbName}/information_schema.tables); do
        mysql -u ${user} -N -B -D ${dbName} -e "SELECT column_name, column_type,
            column_default FROM information_schema.columns
            WHERE table_schema='${dbName}' AND table_name='${table}' ORDER BY
            column_name" --password=${password}  >  \
            ${MINI_CACHE}/${dbName}/${table}.columns
    done
```

4. Run a query to summarize the table relations. Similar formatting rules apply.

```
    mysql -B -N -u ${user} -h ${host} -e "SELECT table_name, column_name,
        referenced_table_name, referenced_column_name FROM key_column_usage
        WHERE referenced_table_name IS NOT NULL AND table_schema='${dbName}'
        ORDER BY table_name, column_name" --password=${password}  > \
        ${MINI_CACHE}/${dbName}/information_schema.key_column_usage
```

5. Update the list of databases known to your RDBMS.

    `mysql -B -N -u ${user} -h ${host} -e "SELECT schema_name FROM
    information_schema.schemata" --password=${password}  >  databases`
