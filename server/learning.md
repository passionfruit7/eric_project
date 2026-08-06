# Learning History

Issue:

date = None

Fix:

Use:

os.stat(path).st_mtime

--------------------------------

Issue:

size = 0B

Fix:

Verify:

os.path.isfile(path)

before reading metadata.