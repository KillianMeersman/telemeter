#!/bin/bash

new_version="$1"
old_version="$(git tag | grep -E 'v.*\..*\..*' | sort -V | tail -n 1 | sed -E 's/v(.*)/\1/')"

if [[ $(git branch --show-current) != 'master' ]]; then
    echo 'Not on dev branch'
    exit -1
fi

echo "Upgrading from $old_version to $new_version"

upload_pypi() {
    python3 -m build
    python3 -m twine upload --repository pypi dist/*
}

# Change source version
sed -i -E "s/version=\"$old_version\"/version =\"$new_version\"/" setup.py

# Create git tag
git commit -a -m "Version $new_version"
git tag -a "v$new_version" -m "Version $new_version"


# Confirm before pushing
read -p "Creating new release $new_version, finalize? (y/N)" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin "v$new_version"
    git push
    upload_pypi
    echo 'Release finalized'
else
    git tag -d "v$new_version"
    sed -i -E "s/version = \"$new_version\"/version = \"$old_version\"/" pkg/config/config.go
    echo 'Aborted'
fi
