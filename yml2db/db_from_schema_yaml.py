# coding: utf-8
"""
# TODO:
# add index
# postgres user-defined type such as enum，must have default
"""

import sys
import os

if sys.version_info[0] == 3:
    import configparser as cfgpsr
else:
    import ConfigParser as cfgpsr
from codecs import open

import yaml

# db connection and cursor
DBCONN = None
DBCUR = None


def get_db_tables(engine):
    if engine == 'mysql':
        DBCUR.execute('show tables')
    else:
        DBCUR.execute("""SELECT c.relname AS Tables_in FROM pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE pg_catalog.pg_table_is_visible(c.oid) AND c.relkind = 'r' AND relname NOT LIKE 'pg_%'
        ORDER BY 1""")

    table_names = [t[0] for t in DBCUR.fetchall()]

    db_tables = {}
    for table_name in table_names:
        if engine == 'mysql':
            DBCUR.execute("describe %s" % table_name)
            # got:
            # Field, Type, Null, Key, Default, Extra
        else:
            # this can also be used for mysql
            # but it won't tell the size
            DBCUR.execute("""select column_name, data_type, is_nullable, 1, column_default, 1, character_maximum_length
            from INFORMATION_SCHEMA.COLUMNS where table_name = '%s'""" % table_name)
        db_tables[table_name] = DBCUR.fetchall()

    return db_tables


def get_default_str(column):
    if 'd' in column:
        d = "set default '%s'" % column['d']
    else:
        d = "drop default"
    return d


def get_null_default_str(column):
    if 'n' in column:
        n = column['n'] and "NULL" or "NOT NULL"
    else:
        n = ""
    if 'd' in column:
        d = "default '%s'" % column['d']
    else:
        d = ""
    return n, d


def coerce_ymc_type(s, engine):
    if engine == 'postgres':
        if s == 'int':
            return 'integer'
        else:
            return s

    if s == 'int':
        return 'int(11)'
    elif s == 'medianint':
        return 'medianint(8)'
    elif s == 'smallint':
        return 'smallint(6)'
    elif s == 'tinyint':
        return 'tinyint(4)'
    else:
        return s


def coerce_dbc_type(s, engine):
    if engine == 'mysql':
        return s

    if s.startswith("character varying"):
        return s.replace("character varying", "varchar")
    else:
        return s


def get_db_column(c, t):
    """
    columns:
        0: name
        1: type
        2: isnull
        3: key(mysql) 1(postgres)
        4: default
        5: extra(mysql) 1(postgres)
        6: size(postgres only)
    """
    for column in t:
        if column[0] == c:
            isnull = column[2] == 'YES'
            if column[1] == 'timestamp without time zone':
                column1 = 'timestamp'
            elif column[1] == 'USER-DEFINED':
                # user-defined such as enum must have default
                column1 = column[4].split('::')[1]
            else:
                column1 = column[1]
            if column[4]:
                column4 = column[4].split('::')[0]
                if column4.startswith("'") and column4.endswith("'"):
                    column4 = column4[1:-1]
            else:
                column4 = None

            if len(column) > 6 and column[6] is not None:
                # postgres character_maximum_length
                column1 = "%s(%s)" % (column1, column[6])
            return {'t': column1, 'n': isnull, 'd': column4}


def update_db(args):
    global DBCONN, DBCUR
    config = cfgpsr.ConfigParser()
    config.read('db_config.ini')
    # cfg = config['db']
    # compatible with both pyton 2 and 3
    cfg = dict(config.items('db'))
    for item in ('engine', 'name', 'user', 'passwd'):
        if item not in cfg:
            exit("%s is required in the config" % item)

    if cfg['engine'] not in ('mysql', 'postgres'):
        exit("Engine `%s` not supported, it's either mysql or postgres" % cfg['engine'])

    if not os.path.isfile(args.schema):
        exit("schema yaml file `%s` doesn't exist" % args.schema)

    with open(args.schema, encoding='utf-8') as f:
        ym_tables = yaml.load(f.read())

    if not isinstance(ym_tables, dict):
        exit("invalid yaml file")

    # Check for 't' in every column
    # change default int value to str
    for t in ym_tables:
        for c in ym_tables[t]:
            if 't' not in ym_tables[t][c]:
                exit("table %s column %s must specify type" % (t, c))
            if 'd' in ym_tables[t][c]:
                if isinstance(ym_tables[t][c]['d'], int):
                    ym_tables[t][c]['d'] = str(ym_tables[t][c]['d'])

    db_server = cfg.get("server", "localhost")
    if cfg['engine'] == 'mysql':
        import pymysql
        db_port = int(cfg.get("port", "3306"))
        DBCONN = pymysql.connect(host=db_server,
                                 port=db_port,
                                 db=cfg['name'],
                                 user=cfg['user'],
                                 passwd=cfg['passwd'])
        DBCUR = DBCONN.cursor()
    else:
        try:
            import psycopg2
        except ImportError:
            exit("`postgres` engine requires package 'psycopg2', please install it with:\n\n\t"
                 "pip install psycopg2\n")

        db_port = int(cfg.get("port", "5432"))
        DBCONN = psycopg2.connect(host=db_server,
                                  port=db_port,
                                  database=cfg['name'],
                                  user=cfg['user'],
                                  password=cfg['passwd'])
        DBCUR = DBCONN.cursor()
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, DBCUR)

    db_tables = get_db_tables(cfg['engine'])

    # find tables that need to be created, deleted, altered
    add_tables = [t for t in ym_tables.keys() if t not in db_tables.keys()]
    delete_tables = [t for t in db_tables.keys() if t not in ym_tables.keys()]
    current_tables = [t for t in ym_tables.keys() if t in db_tables.keys()]

    # sql to add tables
    create_table_sql = ""
    for t in add_tables:
        create_table_sql = "%s\nCREATE TABLE %s (\n id" % (create_table_sql, t)
        if cfg['engine'] == 'mysql':
            create_table_sql = "%s int NOT NULL AUTO_INCREMENT PRIMARY KEY" % create_table_sql
        else:
            create_table_sql = "%s SERIAL PRIMARY KEY""" % create_table_sql
        for c in ym_tables[t]:
            nullstr, defaultstr = get_null_default_str(ym_tables[t][c])
            create_table_sql = "%s\n ,%s %s %s %s" % (
                               create_table_sql, c, ym_tables[t][c]['t'], nullstr, defaultstr)
        create_table_sql = "%s\n);\n\n" % create_table_sql

    # sql to delete tables
    drop_table_sql = ""
    for t in delete_tables:
        drop_table_sql = "%s\nDROP TABLE %s;" % (drop_table_sql, t)

    # sql list to alter tables
    alter_table_sql = []
    for t in current_tables:
        db_columns = [a[0] for a in db_tables[t]]
        add_columns = [c for c in ym_tables[t].keys() if c not in db_columns]
        delete_columns = [c for c in db_columns if c not in ym_tables[t].keys() and c != 'id']
        current_columns = [c for c in ym_tables[t].keys() if c in db_columns]
        for c in add_columns:
            nullstr, defaultstr = get_null_default_str(ym_tables[t][c])
            alter_table_sql.append("ALTER TABLE %s ADD COLUMN %s %s %s %s;" %
                                   (t, c, ym_tables[t][c]['t'], nullstr, defaultstr))
        for c in delete_columns:
            alter_table_sql.append("ALTER TABLE %s DROP %s;" % (t, c))
        for c in current_columns:
            db_c = get_db_column(c, db_tables[t])
            ym_type = coerce_ymc_type(ym_tables[t][c]['t'], cfg['engine'])
            db_type = coerce_dbc_type(db_c['t'], cfg['engine'])
            diff_type = ym_type != db_type
            if 'n' in ym_tables[t][c]:
                diff_null = ym_tables[t][c]['n'] != db_c['n']
            else:
                diff_null = not db_c['n']
            if 'd' in ym_tables[t][c]:
                diff_default = ym_tables[t][c]['d'] != db_c['d']
            else:
                diff_default = db_c['d'] is not None
            # print(db_c)
            # print(ym_tables[t][c])
            # print(diff_type, diff_null, diff_default)
            if cfg['engine'] == 'mysql':
                if diff_type or diff_null or diff_default:
                #    print(db_tables[t])
                #    print(db_c)
                #    print(ym_type)
                    nullstr, defaultstr = get_null_default_str(ym_tables[t][c])
                    alter_table_sql.append("ALTER TABLE %s MODIFY %s %s %s %s;" %
                                           (t, c, ym_tables[t][c]['t'], nullstr, defaultstr))
            else:
                if diff_type:
                    # print(ym_type)
                    # print(db_type)
                    alter_table_sql.append("ALTER TABLE %s ALTER COLUMN %s TYPE %s;" %
                                           (t, c, ym_tables[t][c]['t']))
                if diff_null:
                    if ym_tables[t][c]['n']:
                        # from NOT NULL to NULL
                        alter_table_sql.append("ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL;" % (t, c))
                    else:
                        # from NULL to NOT NULL
                        alter_table_sql.append("ALTER TABLE %s ALTER COLUMN %s SET NOT NULL;" % (t, c))
                if diff_default:
                    alter_table_sql.append("ALTER TABLE %s ALTER COLUMN %s %s;" %
                                       (t, c, get_default_str(ym_tables[t][c])))

    cur = DBCONN.cursor()
    if create_table_sql:
        print(create_table_sql)
        if args.force:
            DBCUR.execute(create_table_sql)
            DBCONN.commit()

    if drop_table_sql:
        print(drop_table_sql)
        if args.force:
            DBCUR.execute(drop_table_sql)
            DBCONN.commit()

    if alter_table_sql:
        print("\n".join(alter_table_sql))
        if args.force:
            DBCUR.execute("".join(alter_table_sql))
            DBCONN.commit()

    DBCUR.close()
    DBCONN.close()

    print("")
    if create_table_sql or drop_table_sql or alter_table_sql:
        if args.force:
            print("Datebase written.")
        else:
            print("The database has not been written. \n"
                  "Re-run with '-f' switch to write to database.")
    else:
        print("No change")
