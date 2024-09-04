import os
import requests
import subprocess
from dotenv import dotenv_values
from src.misc import __version__ as version


branch = 'dev-AIO'
files_to_upload = {
    'Sunshine-AIO.exe': 'Output\\Sunshine-AIO.exe',
    # 'Sunshine-AIO-installer.exe': 'Output/Sunshine-AIO-installer.exe' # Development in progress...
}
config = dotenv_values(".env")


def get_current_branch():
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    ).strip().decode('utf-8')


current_branch = get_current_branch()

if current_branch != branch:
    print(f"You must be on the branch '{branch}' to make a release.")
    exit(1)

release_data = {
    "tag_name": version,
    "name": version,
    "body": open('CHANGELOG.md').read()
}

os.system("compile.bat")
# os.system(f"compile_installer.bat {version}") # Development in progress...

response = requests.post(
    f'https://api.github.com/repos/{config["REPO_NAME"]}/releases',
    json=release_data,
    headers={'Authorization': f'token {config["GITHUB_TOKEN"]}'}
)

release_id = response.json().get('id')
print(response.json())

for file_name, file_path in files_to_upload.items():
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file_to_upload:
            requests.post(
                f'https://uploads.github.com/repos/{config["REPO_NAME"]}/releases/{release_id}/assets?name={file_name}',
                headers={'Authorization': f'token {config["GITHUB_TOKEN"]}',
                         'Content-Type': 'application/octet-stream'},
                data=file_to_upload
            )
        print(f"Uploaded {file_name} successfully.")

print(f"Release {version} was created and pushed successfully on the branch '{branch}'.")
