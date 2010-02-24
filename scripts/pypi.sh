cd $WORKSPACE
VENV=$WORKSPACE/venv
source $VENV/bin/activate

PKG=$WORKSPACE/packages
PYPI=$PKG/pypi
BUNDLE=$PKG/bundle
PYBUNDLE=$PKG/amo.pybundle

echo "Taking forever to make a bundle..."
export PIP_DOWNLOAD_CACHE=$PKG/pip-cache

rm -rf $PYBUNDLE
mkdir -p $PKG
pip -q bundle -r requirements-prod.txt $PYBUNDLE

# Now take apart the bundle and make a pypi-like index.
unzip $PYBUNDLE -d $BUNDLE
chmod -R 744 $BUNDLE

mkdir -p $PYPI

cp $BUNDLE/pip-manifest.txt $PYPI

for f in $BUNDLE/build/* $BUNDLE/src/*
do
    PACKAGE=$PYPI/$(basename $f) &&
    mkdir -p $PACKAGE &&
    pushd $f &&
    python setup.py -q sdist &&
    mv dist/* $PACKAGE &&
    popd
done

echo 'Welcome to the cheeseshop'
