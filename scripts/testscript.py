import sys
import os
from pathlib import Path

ownpath = os.path.abspath(__file__)
folder, file = os.path.split(ownpath)
folder = Path(folder)

sys.path.append(str(folder.parent))
print(sys.path)
from testproject.testtools import testimport as timp

print(timp.testfunction())
