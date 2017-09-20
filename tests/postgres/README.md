## testing steps

Create database:

    sudo -u postgres psql < create_db.sql 

Tests:

    yml2db -s schema-01.yml -f

Table `test1` is created, to verify:

    sudo -u postgres psql yml2db_test -c "\d test1"

next:

    yml2db -s schema-02.yml -f
    yml2db -s schema-03.yml -f
    yml2db -s schema-04.yml -f
    yml2db -s schema-05.yml -f

verify after each time.

Insert some data:

    sudo -u postgres psql yml2db_test < test-05.sql 

Add a json column:

    yml2db -s schema-06.yml -f

Insert some more data:

    sudo -u postgres psql yml2db_test < test-05.sql 

This will fail:

    yml2db -s schema-06-fail.yml -f

because we can not change type from jsonb null to jsonb not null with a default value.

To fix this, just remove the column first:

    yml2db -s schema-05.yml -f

Now this should work:

    yml2db -s schema-06-fail.yml -f
