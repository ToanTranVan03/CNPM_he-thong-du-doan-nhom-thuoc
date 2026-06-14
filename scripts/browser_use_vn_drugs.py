"""Demo browser-use: dùng LLM điều khiển Chrome để cào nguồn dược tiếng Việt.

Chỉ dùng khi trang chặn requests hoặc render bằng JavaScript nặng. Với trang tĩnh,
hãy dùng scripts/scrape_vn_drugs.py (nhẹ hơn, không tốn API).

YÊU CẦU:
    - browser-use đã cài (đã xong).
    - Chrome đã cài (đã có: C:/Program Files/Google/Chrome/Application/chrome.exe).
    - API key LLM. Đặt biến môi trường trước khi chạy, ví dụ:
        $env:OPENAI_API_KEY  = "sk-..."     # rồi dùng ChatOpenAI
      hoặc:
        $env:ANTHROPIC_API_KEY = "sk-ant-..."  # rồi dùng ChatAnthropic

Chạy:
    python scripts/browser_use_vn_drugs.py
"""
import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")


async def main():
    # Import trong hàm để file vẫn đọc được khi chưa cấu hình key
    from browser_use import Agent

    # Chọn LLM theo key có sẵn
    if os.getenv("ANTHROPIC_API_KEY"):
        from browser_use import ChatAnthropic
        llm = ChatAnthropic(model="claude-sonnet-4-6")
    elif os.getenv("OPENAI_API_KEY"):
        from browser_use import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini")
    else:
        print("[X] Chưa có ANTHROPIC_API_KEY hoặc OPENAI_API_KEY. Đặt biến môi trường rồi chạy lại.")
        return

    task = (
        "Vào trang https://trungtamthuoc.com/thuoc . "
        "Lấy 10 thuốc đầu tiên, với mỗi thuốc trích: tên thuốc, hoạt chất, nhóm thuốc, chỉ định. "
        "Trả về dưới dạng danh sách JSON."
    )

    agent = Agent(
        task=task,
        llm=llm,
        # browser-use tự dùng Chrome hệ thống; thêm executable_path nếu cần:
        # browser=Browser(executable_path=r"C:/Program Files/Google/Chrome/Application/chrome.exe"),
    )
    result = await agent.run(max_steps=25)
    print("\n=== KẾT QUẢ ===")
    print(result.final_result())


if __name__ == "__main__":
    asyncio.run(main())
