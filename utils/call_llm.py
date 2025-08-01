import os
import google.generativeai as genai

def call_llm(prompt):
    """
    Google Gemini API를 사용하여 LLM 호출
    
    Args:
        prompt (str): LLM에 전달할 프롬프트
        
    Returns:
        str: LLM의 응답 텍스트
    """
    api_key = os.environ.get("GEMINI_API_KEY", "your-gemini-api-key")
    
    if api_key == "your-gemini-api-key":
        raise ValueError("GEMINI_API_KEY 환경변수를 설정해주세요")
    
    # Gemini API 설정
    genai.configure(api_key=api_key)
    
    # Gemini 1.5 Flash 모델 사용 (더 빠르고 안정적)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API 호출 실패: {str(e)}")

if __name__ == "__main__":
    prompt = "오늘 점심 뭐 먹지? 간단하게 추천해줘."
    print(call_llm(prompt))
