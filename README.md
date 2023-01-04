# uv-std-app
Check if standards' peaks drift during a chromatography run

## Instructions

#### clone and `cd`
```shell
git clone git@github.com:chanana/uv-std-app.git
cd uv-std-app
```

#### if you have poetry use
```shell
poetry install
poetry run pre-commit install
poetry shell
```


#### else
make virtual environment, activate it and install requirements

```shell
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
```

### start app
```shell
python uv-std-app.py
```

In order to run on a localhost setting, modify the last line of the file to say:
`app.run_server()` i.e. remove `host='0.0.0.0'` from the parentheses.

---

## Development
submit a PR
