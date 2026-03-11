import requests
import json

# Send the mock docx with an absolute path as the filename (simulating older browsers or some drag-and-drop cases)
files = {
    'resume': (r'C:\Users\hkyar\Downloads\test_mock.docx', open('test_mock.docx', 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
}
resp = requests.post('http://127.0.0.1:5001/scan', files=files)
print(resp.status_code)
print(resp.json())
