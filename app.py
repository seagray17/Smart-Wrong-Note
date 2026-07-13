import streamlit as st
import requests

st.set_page_config(page_title="스마트 오답노트", layout="wide")

st.title("📊 취약점 분석 기능이 탑재된 스마트 오답노트")
st.caption("실시간으로 채점하고, 내가 어떤 개념 단원에 취약한지 차트로 분석해 줍니다.")

with st.sidebar:
    st.header("⚙️ 시험지 설정")
    exam_id = st.text_input("시험 ID 입력", value="2026_03_MATH")

st.subheader("✍️ 내 답안 마킹 (1번 ~ 20번)")
user_answers = {}

for row in range(5):
    cols = st.columns(4)
    for col_idx in range(4):
        q_num = row * 4 + col_idx + 1
        with cols[col_idx]:
            user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}", value="")

st.divider()

if st.button("🚀 전 문항 일괄 채점 및 분석하기", type="primary"):
    with st.spinner("데이터 분석 및 채점 동기화 중..."):
        payload = {
            "exam_id": exam_id,
            "user_answers": user_answers
        }
        
        try:
            response = requests.post("http://127.0.0.1:8000/api/grade", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                
                st.success(f"💯 채점 완료! 내 성적: {result['score']}")
                
                if result['wrong_count'] == 0:
                    st.balloons()
                    st.info("와우! 만점입니다! 취약한 단원이 없습니다. 🎉")
                else:
                    tag_counts = {}
                    for item in result['wrong_questions']:
                        for tag in item['concept_tags']:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    
                    # 📊 이 부분을 수정했습니다!
                    if tag_counts:
                        st.subheader("📊 내 취약 개념 통계 분석")
                        st.caption("틀린 문제들의 개념 태그를 분석한 결과입니다.")
                        
                        # 💡 horizontal=True 옵션을 넣어 가로형 막대그래프로 변경! 
                        # 이렇게 하면 글자가 절대 아래로 눕지 않고 왼쪽에서 똑바로 보입니다.
                        st.bar_chart(tag_counts, horizontal=True)
                    
                    st.divider()
                    
                    # 오답노트 리스트 출력
                    st.subheader(f"❌ 틀린 문제 오답 노트 ({result['wrong_count']}문항)")
                    
                    for item in result['wrong_questions']:
                        with st.container(border=True):
                            st.markdown(f"### ❓ {item['question_number']}번 문제")
                            st.markdown(f"**🏷️ 출제 개념:** {', '.join(item['concept_tags']) if item['concept_tags'] else '지정 없음'}")
                            st.error(f"내가 제출한 답: {item['user_answer']}  |  **실제 정답: {item['correct_answer']}**")
                            
                            st.divider()
                            
                            st.markdown("#### ✍️ 클라우드 오답 기록장")
                            user_memo = st.text_area(
                                "틀린 원인이나 풀이 팁을 적어두세요.", 
                                value=item['saved_memo'],
                                key=f"input_{exam_id}_{item['question_number']}"
                            )
                            
                            if st.button("💾 DB에 영구 저장하기", key=f"btn_{exam_id}_{item['question_number']}"):
                                save_payload = {
                                    "exam_id": exam_id,
                                    "question_number": item['question_number'],
                                    "user_memo": user_memo
                                }
                                save_res = requests.post("http://127.0.0.1:8000/api/save-note", json=save_payload)
                                
                                if save_res.status_code == 200:
                                    st.toast(f"🎉 {item['question_number']}번 오답 메모가 영구 저장되었습니다!")
                                else:
                                    st.error("메모 저장 실패 😭")
                                
            elif response.status_code == 404:
                st.error("입력하신 시험 ID 정보가 없습니다.")
        except Exception as e:
            st.error(f"서버 통신 실패: {e}")