import os
import requests
import json
from pathlib import Path
import time

SERVER_URL = "http://127.0.0.1:5001/v1/convert/file"
INPUT_DIR = "/mnt/c/Users/ychoi191/work/pdfs"          # PDF가 들어있는 폴더
OUTPUT_DIR = "/mnt/c/Users/ychoi191/work/output_md"    # 마크다운이 저장될 폴더

# 처리할 파일 확장자
TARGET_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

def process_folder(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # 입력 폴더 확인
    if not input_path.exists():
        print(f"입력 폴더가 없습니다: {input_dir}")
        return

    # 출력 폴더 자동 생성
    output_path.mkdir(parents=True, exist_ok=True)

    # 대상 파일 찾기
    files = [f for f in input_path.iterdir() if f.suffix.lower() in TARGET_EXTENSIONS]
    
    print(f"폴더 스캔: {input_dir}")
    print(f"대상 파일: {len(files)}개")
    print(f"저장 경로: {output_dir}")
    print("-" * 60)

    success_count = 0
    
    for idx, file_path in enumerate(files, 1):
        if convert_and_save_md(file_path, output_path, idx, len(files)):
            success_count += 1
            
    print("-" * 60)
    print(f"전체 완료! (성공: {success_count} / 총: {len(files)})")

def convert_and_save_md(file_path, output_dir, idx, total):
    file_name = file_path.name
    print(f"[{idx}/{total}] 변환 중: {file_name} ...", end=" ", flush=True)
    start_time = time.time()

    try:
        with open(file_path, 'rb') as f:
            # 1. 파일 및 옵션 설정
            files = {'files': (file_name, f, 'application/pdf')}
            data = {
                'target_type': 'inbody',
                'options': json.dumps({
                    "do_ocr": False,              # OCR 켜기 (한글 인식 필수)
                    "do_table_structure": True,  # 표 구조 인식 켜기
                    "generate_picture_images": True
                })
            }

            # 2. 서버 요청
            response = requests.post(SERVER_URL, files=files, data=data, timeout=300)

        # 3. 응답 처리
        if response.status_code == 200:
            result = response.json()
            
            md_content = result.get("document", {}).get("md_content", "")

            if md_content:
                # .md 파일로 저장
                save_path = output_dir / f"{file_path.stem}.md"
                with open(save_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(md_content)
                
                elapsed = time.time() - start_time
                print(f"성공 ({elapsed:.1f}초) -> {save_path.name}")
                return True
            else:
                print(" 경고: 변환 결과(Markdown)가 비어있습니다.")
                return False

        else:
            print(f"실패 (Status: {response.status_code})")
            # 에러 메시지 확인
            try:
                print(f"   └─ {response.json().get('detail', '알 수 없는 오류')}")
            except:
                pass
            return False

    except Exception as e:
        print(f"\n에러 발생: {e}")
        return False

if __name__ == "__main__":
    process_folder(INPUT_DIR, OUTPUT_DIR)