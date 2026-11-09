# Releasing sindhinorm to PyPI

Commands are for Windows PowerShell, run from `C:\Projects\Morph\morphtok-sd-ur\packages\sindhinorm`.
`py` below means the project's Python: `..\..\.venv\Scripts\python.exe`.

## One-time setup

1. **Accounts.** Create two separate accounts with the same email: https://test.pypi.org/account/register/
   (practice) and https://pypi.org/account/register/ (real). Verify the email on both.
2. **Two-factor authentication.** Both sites require it before you can upload: *Account settings →
   Add 2FA* (an authenticator app, or a security key). Save the recovery codes.
3. **API tokens.** On each site: *Account settings → API tokens → Add API token*, name
   `sindhinorm`, scope **Entire account** (a project-scoped token can only be made after the first
   upload). Copy the token (starts with `pypi-`); it is shown once. Keep it like a password.
4. **Tools.**
   ```powershell
   ..\..\.venv\Scripts\python.exe -m pip install --upgrade build twine
   ```

## Every release

5. **Push the code to GitHub first**, so the Homepage link on PyPI works.
6. **Set the version** in two places (they must match):
   `pyproject.toml` (`version = "0.1.0"`) and `src\sindhinorm\__init__.py` (`__version__`).
   A version number can be uploaded only once, ever. A fix after release needs 0.1.1.
7. **Run the tests** from the repository root:
   ```powershell
   cd ..\..; .venv\Scripts\python.exe -m pytest -q tests\test_sindhinorm.py; cd packages\sindhinorm
   ```
8. **Build fresh files.**
   ```powershell
   Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
   ..\..\.venv\Scripts\python.exe -m build
   ```
   This makes `dist\sindhinorm-<version>-py3-none-any.whl` and `dist\sindhinorm-<version>.tar.gz`.
9. **Check them.**
   ```powershell
   ..\..\.venv\Scripts\python.exe -m twine check dist/*
   ```
   Both must say `PASSED`.
10. **Upload to TestPyPI.**
    ```powershell
    ..\..\.venv\Scripts\python.exe -m twine upload --repository testpypi dist/*
    ```
    Username: `__token__`. Password: your **TestPyPI** token (the paste is invisible; that is normal).
11. **Install it from TestPyPI in a throwaway environment** and try it:
    ```powershell
    py -m venv $env:TEMP\sn-test
    & "$env:TEMP\sn-test\Scripts\pip.exe" install -i https://test.pypi.org/simple/ sindhinorm
    & "$env:TEMP\sn-test\Scripts\sindhinorm.exe" explain "ھن آهی کري"
    ```
    Expect three lines ending in `[encoding-merge]`, `[encoding-merge]`, `[native-keep]`.
    Also look at https://test.pypi.org/project/sindhinorm/: README, licences, links.
12. **Upload to the real PyPI.**
    ```powershell
    ..\..\.venv\Scripts\python.exe -m twine upload dist/*
    ```
    Username `__token__`, password your **PyPI** token. Anyone can now `pip install sindhinorm`.
13. **Tighten the token (first release only).** On pypi.org create a new token scoped to
    *Project: sindhinorm*, use it from now on, and delete the *Entire account* token. Do the same
    on TestPyPI.
14. **Tag the release** in git: `git tag sindhinorm-v0.1.0` and `git push origin sindhinorm-v0.1.0`.

## Optional

* Save tokens so twine stops asking: create `%USERPROFILE%\.pypirc` with sections
  `[pypi]` and `[testpypi]`, each with `username = __token__` and `password = <token>`.
  Anyone who can read that file can publish as you.
* Later, PyPI "Trusted Publishing" from GitHub Actions removes tokens entirely
  (https://docs.pypi.org/trusted-publishers/).
