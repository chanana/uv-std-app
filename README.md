# uv-std-app
Check if standards' peaks drift during a chromatography run

## Instructions
```shell
# clone
git clone git@github.com:chanana/uv-std-app.git

# cd into directory
cd uv-std-app

# make virtual environment
python -m venv .venv

# activate virtual environment
source .venv/bin/activate

# install libraries
pip install --upgrade pip wheel
pip install -r requirements.txt

# start app
python uv-std-app.py
```

In order to run on a localhost setting, modify the last line of the file to say:
`app.run_server()` i.e. remove `host='0.0.0.0'` from the parentheses.