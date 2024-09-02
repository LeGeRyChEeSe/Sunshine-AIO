import os
import requests
import subprocess
from dotenv import dotenv_values
from src import __version__ as version


branch = 'dev-AIO'
exe_file_path = f'dist/Sunshine-AIO.exe'
config = dotenv_values(".env")


def get_current_branch():
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    ).strip().decode('utf-8')


current_branch = get_current_branch()

if current_branch != branch:
    print(f"You must be on the branch '{branch}' to make a release.")
    exit(1)

os.system("pyinstaller main.spec")


release_data = {
    "tag_name": version,
    "name": version,
    "body": open('CHANGELOG.md').read()
}

response = requests.post(
    f'https://api.github.com/repos/{config["REPO_NAME"]}/releases',
    json=release_data,
    headers={'Authorization': f'token {config["GITHUB_TOKEN"]}'}
)

release_id = response.json().get('id')
print(response.json())

# Uploader le fichier .exe
with open(exe_file_path, 'rb') as exe_file:
    requests.post(
        f'https://uploads.github.com/repos/{config["REPO_NAME"]}/releases/{release_id}/assets?name={os.path.basename(exe_file_path)}',
        headers={'Authorization': f'token {config["GITHUB_TOKEN"]}',
                 'Content-Type': 'application/octet-stream'},
        data=exe_file
    )

print(f"Release {version} was created and pushed successfully on the branch '{branch}'.")
