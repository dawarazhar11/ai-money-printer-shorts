import requests

url = "https://api.heygen.com/v1/video_status.get?video_id=5169ef5a328149a8b13c365ee7060106"

headers = {
    "accept": "application/json",
    "x-api-key": "Y2UyMGY2NTZmZTNjNDhiYjk1MjhjZDUwNzlkMWJjMTEtMTc0NzcyMTE2OA=="
}

response = requests.get(url, headers=headers)

print(response.text) 