## notes

To publish to pypi:

    vi setup.py  # change version
    cat ~/.pypirc   # make sure exists
    rm dist/*  # remove previous version in dist
    python setup.py sdist 
    python setup.py bdist_wheel --universal
    twine upload dist/*
