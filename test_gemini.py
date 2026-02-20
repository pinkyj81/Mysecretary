from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

print("사용 가능한 모델 목록:")
try:
    models = client.models.list()
    for model in models:
        print(f"- {model.name}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"  지원 메서드: {model.supported_generation_methods}")
except Exception as e:
    print(f"모델 목록 조회 실패: {e}")

print("\n간단한 테스트:")
try:
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='안녕하세요'
    )
    print(f"성공: {response.text}")
except Exception as e:
    print(f"실패: {e}")
