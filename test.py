import requests

url = "http://127.0.0.1:5001/v1/convert/file"

file_path = '/home/shaush/projects/pdfs/정리.pdf'

try:
    with open(file_path, 'rb') as f:

        files = {
            'files': ('document.pdf', f, 'application/pdf')
        }
        
        data = {
            "do_table_structure": "true",
            "format": "md"
        }

        print(f"Sending request to {url}...")
        response = requests.post(url, files=files, data=data)

    # 3. 결과 확인
    if response.status_code == 200:
        print("성공")
        print(response.text)
        
    else:
        print(f"실패 (Status: {response.status_code})")
        print("서버 응답:", response.text)

except Exception as e:
    print("연결 에러:", e)