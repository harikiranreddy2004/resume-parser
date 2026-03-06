import requests

url = "http://127.0.0.1:5001/scan"
file_path = "test_resume.txt"

with open(file_path, "rb") as f:
    files = {"resume": f}
    response = requests.post(url, files=files)

print(f"Status Code: {response.status_code}")
print("Response Data:")
print(response.json())
