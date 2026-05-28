#!/bin/sh

echo "App started..."
echo "Hello $NAME"
echo "Working Directory: $(pwd)"

# create a file (for isolation demo)
echo "inside container" > /testfile.txt
echo "New change added"
echo "change test"
echo  "FINAL CHANGE"
echo  "check final"
echo "App finished"
