qq_sample_db: homemade data for pre-alpha testing-as-you-go
third-party/mywind: a port of Microsoft's Northwind db from SQL Server to MySQL

Steps:
1. Create these dbs manually
    `mysql -u root -e "CREATE DATABASE foo"`
2. Populate using the \*.sql files found in here
    `mysql -u root -D foo < foo.sql`
3. Create cached schema information for db and tables;
    The software expects tab-delimited fields.
    `mysql -u <user> -B -N -e "SELECT... FROM ... WHERE .. AND table_schema='<dbName>'"  >  <cached_data_filename>`
