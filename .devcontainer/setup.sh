#!/bin/bash
# Redirect all heavy dirs off the 504MB root to kataShared

if [ "$1" == "--cleanup" ]; then
  # Wipe everything from kataShared
  echo "Cleaning up kataShared..."
  rm -rf /.dockerenv/npm-cache
  rm -rf /.dockerenv/node_modules
  rm -rf ./node_modules
  mkdir -p ./node_modules
  echo "✓ kataShared wiped clean"
  exit 0
fi

mkdir -p /.dockerenv/npm-cache
mkdir -p /.dockerenv/node_modules

# Symlink node_modules if not already done
if [ ! -L ./node_modules ]; then
  rm -rf ./node_modules
  ln -s /.dockerenv/node_modules ./node_modules
fi

echo "✓ npm redirected to kataShared (188GB free)"
