# 🧠 ADHD Daily Dashboard

> **ADHD 사용자의 실행 기능과 집중력을 보완하기 위해 설계된 데스크톱 플래너.**  

## ✨ 주요 기능

*   **📅 달력**: 과거의 기록을 쉽게 확인하고 오늘 및 미래의 계획을 세울 수 있습니다.

*   **🎯 Top 3 Goals**: 하루의 핵심 목표 3가지를 우선순위에 따라 관리하며, 화살표 버튼으로 자유롭게 순서를 변경 가능.

*   **🕒 Time Blocks**: 일정 조절. Top 3 Goals와 마찬가지로 화살표 버튼으로 순서 변경 가능,

*   **🍅 포모도로 타이머**: 기본 25분. 원하는 시간을 직접 입력하여 집중 시간을 관리.

*   **📊 주간 인사이트 리포트**: 지난 7일간의 목표 달성률과 에너지 레벨을 시각화된 그래프로 한눈에 파악합니다.

*   **🎲 결정 룰렛 (Pick One)**: Top 3 Goals의 목표 중 하나를 랜덤으로 선택하고 최상단으로 올려줍니다.

*   **📌 플로팅 미니 모드**: 미니 모드 사용시 Top 3 Goals의 최상단 목표 하나만 출력. (투명도 조절 가능)

*   **🎉 팡파레 효과음**: 모든 목표 달성 시 화면 가득 폭죽 애니메이션과 함께 축하 효과음(`fanfare.mp3`)이 재생됩니다.

*   **📥 시스템 트레이**: 창을 닫아도 배경에서 계속 작동하며 시스템 트레이에서 언제든 다시 불러올 수 있습니다.

## 🛠 Tech Stack

- **Language**: Python 3.12+
- **GUI Framework**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (Modern UI)
- **Data Persistence**: JSON based local storage
- **Graphics**: Matplotlib (Weekly stats)
- **Audio**: Pygame mixer
- **OS Integration**: Pystray (System Tray), Plyer (Notifications)

## 🚀 시작하기

### 필수 라이브러리 설치
```bash
pip install customtkinter matplotlib pygame pystray Pillow plyer
```

### 실행 방법
```bash
python main.py
```

### 📝 참고 사항
- exe 파일의 위치에 data 폴더를 생성 후 json의 형태로 저장함.
- AI를 사용하여 작성된 코드.